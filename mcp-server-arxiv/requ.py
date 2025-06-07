# import requests

# url = "http://127.0.0.1:5000/mcp-server/mcp"
# headers = {
#     "Accept": "text/event-stream",
#     "Content-Type": "application/json"
# }
# payload = {
#     "name": "arxiv_search",
#     "arguments": {
#         "query": "quantum entanglement",
#         "max_results": 2,
#         "max_text_length": 1000
#     }
# }

# response = requests.post(url, json=payload, headers=headers, stream=True)

# for line in response.iter_lines():
#     if line:
#         print(line.decode())



# import httpx


# payload = {
#     "name": "arxiv_search",
#     "arguments": {
#         "query": "quantum entanglement",
#         "max_results": 2,
#         "max_text_length": 1000
#     }
# }


# with httpx.post("http://localhost:5000/mcp-server/mcp", headers={
#     "Accept": "text/event-stream",
#     "Content-Type": "application/json",
# }, json=payload) as response:
#     for line in response.iter_lines():
#         print(line)






import httpx
session_id = "325118cd565f43b2b4aa9f2f74202fed"
payload = {
    "jsonrpc": "2.0",
    "method": "arxiv_search",
    "params": {
        "query": "quantum entanglement",
        "max_results": 2,
        "max_text_length": 1000
    },
    "id": 1
}

with httpx.stream("POST", "http://localhost:5000/mcp-server/mcp/", headers={
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}, json=payload) as response:
    print("Status code:", response.status_code)
    print("Headers:", response.headers)

    for line in response.iter_lines():
        if line:
            print("Line:", line)
        else:
            print("Received empty line")