import requests

class EmbeddingClient:
    def __init__(self, api_url, api_key, model):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def get_embedding(self, text):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": self.model,
            "input": text,
            "encoding_format": "float"
        }
        response = requests.post(self.api_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['data'][0]['embedding']
        else:
            raise Exception(f"API error: {response.text}")
        
if __name__ == "__main__":
    url = "https://api.siliconflow.cn/v1/embeddings"
    api = "sk-lcmgoofhdtzibdjvizbzzuyuvmwnuzavvdrabokwstieedal"
    model = "BAAI/bge-m3"
    text = "hello sdp"
    embedding_client = EmbeddingClient(url, api, model)
    embedding = embedding_client.get_embedding(text)
    print(embedding)
