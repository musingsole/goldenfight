from flask import Flask, Response

if __name__ == '__main__':
    app = Flask(__name__)

    def scale():
        with open("webpages/scale.html", "r") as f:
            page = f.read()
        return Response(page, status=200)

    @app.route('/scale_reader.html')
    def scale_reader():
        with open("webpages/scale_reader.html", "r") as f:
            page = f.read()
        page = page.replace("{current_value}", "0.00")
        page = page.replace("{calibration_unit}", "lbs")
        return Response(page, status=200)

    @app.route('/mode_menu.html')
    def mode_menu():
        with open("webpages/mode_menu.html", "r") as f:
            page = f.read()
        return Response(page, status=200)

    @app.route('/adjustment_menu.html')
    def adjustment_menu():
        with open("webpages/adjustment_menu.html", "r") as f:
            page = f.read()
        return Response(page, status=200)

    @app.route('/')
    def configuration():
        with open("webpages/configuration.html", "r") as f:
            page = f.read()
        return Response(page, status=200)

    app.run(port=9999)
