import asyncio
from datetime import datetime
from traceback import format_exc as generate_traceback


def no_log(*args, **kwargs):
    return


def default_log(message):
    dt = datetime.utcnow()
    print("{} | {}".format(dt, message))


def run_async(func,
              arg_sets,
              log=no_log,
              log_reduction_factor=8):
    results = {}

    log("Beginning Asynchronous Execution for {} argument sets".format(len(arg_sets)))
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)

        def get_results(func, arg_set, enumeration):
            if type(arg_set) is list:
                return enumeration, func(*arg_set)
            else:
                return enumeration, func(**arg_set)

        async def run_arg_sets(loop):
            futures = [loop.run_in_executor(None, get_results, func, arg_set, e) for e, arg_set in enumerate(arg_sets)]
            for f in asyncio.as_completed(futures):
                e, result = await f
                results[e] = result
                if int(len(arg_sets) / log_reduction_factor) > 0:
                    if len(results) % int(len(arg_sets) / log_reduction_factor) == 0:
                        log("Completed {} of {}".format(len(results), len(arg_sets)))
        loop.run_until_complete(run_arg_sets(loop))
        log("Asynchronous execution complete")
        results = [results[i] for i in range(len(arg_sets))]
    except Exception as e:
        print("Failed: {}".format(e))
        print(generate_traceback())
    finally:
        loop.close()

    return list(zip(arg_sets, results))
