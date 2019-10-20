from LambdaPage import LambdaPage
import os
import json


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_fw_filenames(event=None, fw_dir="FiPy"):
    with open("{}/goldenfight.json".format(fw_dir), "r") as f:
        goldenfight = json.loads(f.read())

    goldenfight['files'] = os.listdir(fw_dir)

    return json.dumps(goldenfight)


def get_fw_file(event, max_chunk_size=800):
    filename = event['path'].replace("/ota", "")
    if 'chunk' in event['queryStringParameters']:
        chunk_index = int(event['queryStringParameters']['chunk'])
    else:
        chunk_index = 0

    if not os.path.exists("FiPy/{}".format(filename)):
        print("{} not found".format(filename))
        return 404, "File {} not found".format(filename)

    with open("FiPy/{}".format(filename), "r") as f:
        content = f.read()

    content_chunks = list(chunks(content, max_chunk_size))

    if content_chunks is None:
        raise Exception("Firmware repository misconfigured with empty file!")

    print("Recovered {}. Total Chunks: {}. Returning Chunk {}".format(filename, len(content_chunks), chunk_index))

    response = {
        "filename": filename,
        "chunk_index": chunk_index,
        "total_chunks": len(content_chunks),
        "content_chunk": content_chunks[chunk_index]
    }

    print("Returning Chunk {} of {}".format(chunk_index, filename))
    return 200, response


def init_lambda_page():
    page = LambdaPage()

    # Account manage portion
    page.add_endpoint('get', '/ota', get_fw_filenames, 'application/json')
    page.add_endpoint('get', '/ota/{filename}', get_fw_file, 'application/json')

    return page


def lambda_handler(event, context):
    print("Received Event: {}".format(event))
    resp = init_lambda_page().handle_request(event)
    print("Returning response: {}".format(resp))
    return resp


if __name__ == "__main__":
    init_lambda_page().start_local()
