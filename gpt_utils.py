import openai


def summarize_email(user: str, message: str) -> str:
    """
    Returns a 1-2 sentence summary of the given message.

    :param user: The user, whom which the system will refer to as "you".
    :param message: The email contents.
    """

    summary = (
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""I am {user}. Refer to all instances of {user} as "you". Summarize the given emails in 2 short sentences or fewer.
                            
                            Example summary 1: You sent a message to person B asking them for an internship. You were inspired by their talk at the YC event and gave them your contact information.
                            Example summary 2: John Doe responded to you saying that they were impressed with your resume and would like to set up a meeting with you.
                            """,
                },
                {
                    "role": "user",
                    "content": f"{message}",
                },
            ],
            temperature=0.05,
        )
        .choices[0]  # type: ignore
        .message.content
    )

    return summary
