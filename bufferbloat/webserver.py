from http.server import SimpleHTTPRequestHandler
import socketserver

PORT = 80

httpd = socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler)
print("Server1: httpd serving at port", PORT)
httpd.serve_forever()
