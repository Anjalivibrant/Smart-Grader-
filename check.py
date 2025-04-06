import google.generativeai as genai

genai.configure(api_key="AIzaSyA8MC0w5P11wIGeO3JeI66jdkSq2xBu2B0")
models = genai.list_models()

for model in models:
    print(model.name)
