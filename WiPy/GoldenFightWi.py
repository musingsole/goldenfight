import os
import json
from machine import Timer, reset
from time import sleep, sleep_ms
from sys import print_exception

from WiPyFunctions import get_timestamp, get_device_id, enable_ntp
from WiPyFunctions import LED_BLUE, LED_GREEN, LED_OFF
from WiPyFunctions import button_handler, reset_handler, log_message

from woodwellWi import woodwell, Memory
from HTTPServer import http_daemon, build_response, set_wlan_to_access_point, success, failure, unquote, parse_querystring
from ScaleInterface import Scale


class GoldenFight(dict):
    @staticmethod
    def clear_device(*args, **kwargs):
        log_message("Processing halted. Clearing device")

        sleep(5)

        # Remove stored configuration, resetting device to freshly
        # installed state
        os.remove("GoldenFight.json")

        reset_handler()

    def save_woodwell(self):
        with open("woodwell", "w") as f:
            f.write(str(self.woodwell))

    def __init__(self, FLASHING_LIGHT, start_web_server=True):
        self.FLASHING_LIGHT = FLASHING_LIGHT
        self.FLASHING_LIGHT.set_milliseconds(500)

        # Flash light green and blue to show device has connected to network and is registering with Mobius
        self.FLASHING_LIGHT.colors = [LED_BLUE, LED_GREEN] + [LED_OFF] * 4

        # Configure push button to clear device
        self.button = button_handler(self.clear_device)

        # Build Scale
        self.scale = Scale()
    
        self.FLASHING_LIGHT.colors = [LED_GREEN, LED_BLUE] + [LED_OFF] * 4

        print("Recovering or building memory system")
        try:
            with open("woodwell", "r") as f:
                self.woodwell = woodwell(name='woodwell', woodwell=f.read())
        except Exception as e:
            print("Failed to recover woodwell. Building new memory")
            self.woodwell = woodwell('woodwell')
            self.save_woodwell()
    	
        print("Recovering configuration")
        self.calibration_factor()
        self.calibration_unit()
        self.tare_point()
        self.aggregated()
        self.ssid()
        self.password()    

        self.FLASHING_LIGHT.colors = [LED_GREEN, LED_BLUE] + [LED_OFF] * 3

        self.wlan = set_wlan_to_access_point(
            ssid="goldenfight_" + get_device_id(),
            password="musingsole"
        )

        self.FLASHING_LIGHT.colors = [LED_GREEN] + [LED_OFF] * 10

    def attribute(self,
                  tree,
                  new=None,
                  default=None,
                  return_filter=lambda x: float(x)):
        if new is None:
            mems = self.woodwell.remember(tree=tree, Limit=1)
            if len(mems) == 0 and default is not None:
                mems = [Memory(TREE=tree, TRUNK='attribute', VALUE=default)]
                self.woodwell.memorize(mems)
                self.save_woodwell() 
            current = mems[0]['VALUE']
            if return_filter is not None:
                current = return_filter(current)
            return current
        else:
            new_mem = Memory(TREE=tree, TRUNK='attribute', VALUE=new)
            self.woodwell.memorize([new_mem])
            self.save_woodwell()

    ## Attribute interface functions

    def calibration_factor(self, new=None):
        return self.attribute(
            'calibration_factor',
            new,
            default=1)
    def calibration_unit(self, new=None):
        return self.attribute(
            'calibration_unit',
            new,
            default='lbs',
            return_filter=None)

    def tare_point(self, new=None):
        return self.attribute('tare_point', new, default=0)
	
    def aggregated(self, new=None):
        return self.attribute('aggregated', new, default=0)
	
    def ssid(self, new=None):
        return self.attribute(
            'ssid',
            new,
            default='goldenfight',
            return_filter=None)

    def password(self, new=None):
        return self.attribute(
            'password',
            new,
            default='musingsole',
            return_filter=None)

    ## Scale Functions

    def get_scale_reading(self, samples=5, attempts=5):
        while attempts > 0:
            attempts -= 1
            try:
                scale_results = []
                while len(scale_results) < samples:
                    try:
                        result = self.scale.read()
                    except Exception:
                        sleep_ms(2)
                        continue
                    scale_results.append(result)
                    sleep_ms(1)

                scale_results = sorted(scale_results)
                result_median = scale_results[int(len(scale_results) / 2)]
                return result_median
            except Exception as e:
                print("Failed Scale Read Attempt")
                print_exception(e)

        raise Exception("Failed to get scale reading")

    def get_current_reading(self, samples=5):
        try:
            reading = self.get_scale_reading()
            current_value = (reading - float(self.tare_point())) / float(self.calibration_factor())
        except Exception:
            print("Failed to get scale reading")
            current_value = -999999

        return current_value

    ## Webpage Support Functions

    def get_page(self, path):
        with open(path, 'r') as f:
            page = f.read()
        return page

    def build_configuration_page(self, msg=""):
        path = "webpages/configuration.html"
        page = self.get_page(path)
        page = page.replace("{message}", msg)
        
        page = page.replace("{current_value}", "{:.2f}".format(self.get_current_reading()))
        page = page.replace("{calibration_unit}", str(self.calibration_unit())) 
        page = page.replace("{tare_point}", str(self.tare_point()))
        page = page.replace("{calibration_factor}", str(self.calibration_factor()))
        return page

    def build_aggregate_page(self, msg=""):
        path = "webpages/aggregate.html"
        page = self.get_page(path)
        page = page.replace("{message}", msg)

        page = page.replace("{current_value}", "{:.2f}".format(self.get_current_reading()))

        page = page.replace("{next_weight_ready}", "No") 
        page = page.replace("{aggregated_value}", str(self.aggregated())) 
        return page

    def build_scale_page(self, msg=""):
        path = "webpages/scale.html"
        page = self.get_page(path)
        page = page.replace("{message}", msg)
        page = page.replace("{current_value}", "{:.2f}".format(self.get_current_reading())) 
        page = page.replace("{calibration_unit}", str(self.calibration_unit())) 
        return page

    @staticmethod
    def mode_from_body(body):
        if 'configuration' in body:
           return 'configuration' 
        elif 'aggregate' in body:
           return 'aggregate'
        else:
           return 'scale'
       
    ## Webpage Endpoint Functions
    def adjustment_menu(self, request):
        with open('webpages/adjustment_menu.html', 'r') as f:
            page = f.read()
        page = page.replace("{current_value}", "{:.2f}".format(self.get_current_reading()))
        page = page.replace("{calibration_unit}", str(self.calibration_unit()))

        return build_response(body=page)

    def scale_reader(self, request):
        with open('webpages/scale_reader.html', 'r') as f:
            page = f.read()
        page = page.replace("{current_value}", "{:.2f}".format(self.get_current_reading()))
        page = page.replace("{calibration_unit}", str(self.calibration_unit()))

        return build_response(body=page)

    def mode_menu(self, request):
        with open('webpages/mode_menu.html', 'r') as f:
            page = f.read()

        return build_response(body=page)

    def mode(self, request, msg=""):
        print("Mode Received Request:\n{}".format(request))
        try:
            mode = self.mode_from_body(request['body'])
            if 'configuration' == mode:
                page = self.build_configuration_page()
            elif 'aggregate' == mode:
                page = self.build_aggregate_page()
            else:
                page = self.build_scale_page()
       
            return build_response(body=page)
        except Exception as e:
            print("Mode Endpoint Failed")
            print_exception(e)
            return failure

    def tare(self, request):
        reading = self.get_scale_reading(samples=20)
        print("Read {}. Setting as new tare point".format(reading))
        self.tare_point(new=reading) 
        print("New tare point: {}".format(self.tare_point()))

        return build_response(body=self.build_configuration_page())

    def calibrate(self, request):
        req_body = request['body']
        print("Calibrating with {}".format(req_body))
        try:
           
            value, unit = req_body.split("&")
            value = float(value.split("=")[1])
            unit = unit.split("=")[1]
            self.calibration_unit(new=unit)

            current_scale = self.get_scale_reading()
            tare = self.tare_point()
            current_value = current_scale - tare
            factor = current_value / value

            print("Found Factor to be: {}".format(factor))
            self.calibration_factor(new=factor)
        except Exception as e:
            print("Failed to store calibration values")
            print_exception(e)

        return build_response(body=self.build_configuration_page())

    def update(self, request):
        print("Not implemented")
        return build_response(body=self.build_configuration_page())
    
    ## Aggregation Functions

    def aggregate_next(self, request):
        print("Original Aggregated: {}".format(self.aggregated()))
        aggregated = self.aggregated()
        cv = self.get_current_reading()
        aggregated += cv
        self.aggregated(new=aggregated)
        print("New Aggregated: {}".format(self.aggregated()))

        return build_response(body=self.build_aggregate_page())

    def aggregate_clear(self, request):
        self.aggregated(new=0)
        return build_response(body=self.build_aggregate_page())

    def aggregate_tare(self, reqeust):
        try:
            scale_reading = self.get_scale_reading(samples=20)
            self.tare_point(new=scale_reading) 
        except Exception as e:
            print("Failed to tare device (aggregate)")
            print_exception(e)

        return build_response(body=self.build_aggregate_page())

    ## Functional Webapp Endpoints (return data, not pages)

    def current_scale_value(self, request):
        return build_response(body=str(self.get_scale_reading()))

    def remember(self, request):
        qs = unquote(request['query_parameters']).decode()
        query_parameters = parse_querystring(qs)

        tree = query_parameters['tree']
        trunk = query_parameters['trunk'] if 'trunk' in query_parameters else None

        memories = self.woodwell.remember(tree=tree, trunk=trunk)
        return build_response(body=json.dumps(memories))

    def provide_jquery(self, request):
         js = self.get_page("webpage/jquery.min.js")
         return build_response(
             body=js,
             content_type="text/javascript")

    def http_daemon(self, log=print):
        path_to_handler = {
            "/": self.mode,
            "/mode": self.mode,
            "/favicon.ico": lambda req: success,

            # Aggregation Functional Endpoints
            "/aggregate_next": self.aggregate_next,
            "/aggregate_clear": self.aggregate_clear,
            "/aggregate_tare": self.aggregate_tare,

            # Configuration Functional Endpoints
            "/adjustment_menu.html": self.adjustment_menu,
            "/mode_menu.html": self.mode_menu,
            "/scale_reader.html": self.scale_reader,
            "/update": self.update,
            "/calibrate": self.calibrate,
            "/tare": self.tare,

            # Functional Endpoints
            "/remember": self.remember,
            "/scale": self.current_scale_value,
        }

        error_page = self.get_page(path='webpages/error.html')

        error_res = build_response(
            status_code=500,
            body=error_page
        )

        http_daemon(
            log=log,
            path_to_handler=path_to_handler,
            error_response=error_res
        )
