from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Arcade Hub!"

@app.route('/api/data', methods=['GET'])
def get_data():
    data = {"message": "This is your data!"}
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)