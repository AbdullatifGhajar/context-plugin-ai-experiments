from openai import OpenAI


OPENAI_API_KEY = "your-openai-key"

class OpenaiModel:
    def __init__(self, model_id="gpt-4"):
        self.model_id = model_id
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def ask(
        self,
        task: str,
        prompt: str,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
            {"role": "system", "content": task},
            {"role": "user", "content": prompt},
            ],
        )
        answer = response.choices[0].message.content

        if not answer:
            raise ValueError("No answer from Model")
        
        return answer

if __name__ == "__main__":
    gpt_model = OpenaiModel("gpt-4")
    responses = gpt_model.ask("", "how are you?")
    print(responses)
