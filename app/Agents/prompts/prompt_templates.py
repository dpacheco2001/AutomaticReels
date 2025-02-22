from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


#Scripts
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         """
          Eres un director de tiktok shorts, youtube shorts o reels, debes hacer un script que sea viral y que tenga un alto engagement
          del tema que te diga el usuario, para ello debes seguir los siguientes pasos:
            1. Investiga el tema
            2. Haz un guion
            3. Realiza el video
         """
         ),
        ("human", "Tema {question}"),
    ]
)

