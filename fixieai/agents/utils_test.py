import pytest

from fixieai.agents import utils


class ConversationalPrompt:
    """A wrapper type to facilitate testing prompts with/without the conversational flag."""

    def __init__(self, prompt: str):
        self.prompt = prompt

    def __str__(self):
        return self.prompt


BAD_PROMPTS = [
    # Ask Agent without Agent says
    """Q: Who is the president?
Ask Agent[search]: Who is the president?
A: It's Joe Biden.""",
    # Doesn't start with a query
    """Ask Agent[search]: Who is the president?
Q: Who is the president?
A: It's Joe Biden.""",
    # Ask Func without Func says
    """Q: How many books are there in the library?
Ask Func[library]: How many books are there in the library?
A: I don't know.""",
    # Doesn't end with a response
    """Q: What is 12 + 15?
Agent[calc] says: 27""",
    # 2 queries
    """Q: What is the life expectancy in the US?
Q: Do we need to call an agent?
A: No we don't.""",
    # 2 responses
    """Q: What is the life expectancy in the US?
A: I think it's 80 years but I'm not sure.
A: I'm not sure.""",
    # extra whitespace
    """Q: What is the life expectancy in the US?
A: I think it's 80 years but I'm not sure. """,
    # empty line at the end
    """Q: What is the life expectancy in the US?
A: I think it's 80 years but I'm not sure.
""",
    # empty line to start
    """
Q: What is the life expectancy in the US?
    A: I think it's 80 years but I'm not sure.""",
    # Invalid func name
    """Q: How many books are there in the library?
Ask Func[invalid_library]: How many books are there in the library?
Func[invalid_library] says: Many
A: There are many books in the library.""",
    # Mismatched func names
    """Q: How many books are there in the library?
Ask Func[library]: How many books are there in the library?
Func[bibliothèque] says: Many
A: There are many books in the library.""",
    # Mismatched agent names
    """Q: How many books are there in the library?
Ask Agent[library]: How many books are there in the library?
Agent[bibliothèque] says: Many
A: There are many books in the library.""",
    # Conversational without setting the flag
    """Q: Think of your favorite color
A: Okay, I'm thinking of it.
Q: Is it red?
A: No, it's not red.
Q: Is it blue?
A: Yes, it's blue!""",
    # Ask Agent lines aren't allowed between questions
    ConversationalPrompt(
        """Q: Think of your favorite color
A: Okay, I'm thinking of it.
Q: Is it red?
A: No, it's not red.
Ask Agent[library]: How many books are in the library?
Agent[library] says: I shouldn't be invoked between questions.
Q: Is it blue?
A: Yes, it's blue!"""
    ),
    # Ask Agent lines can't introduce new embeds
    """Q: What's the weather?
Ask Agent[weather]: What's the weather in #image1
Agent[weather] says: cloudy.
A: It's cloudy.""",
    # Ask Func lines can't introduce new embeds
    """Q: What's the weather?
Ask Func[weather]: #image1
Func[weather] says: cloudy.
A: It's cloudy.""",
    # Response lines can't introduce new embeds
    """Q: What's the weather?
A: Here's a picture of the weather #image1""",
    # Query lines must have a query
    """Q:
A: That's not a question!""",
]


@pytest.fixture
def is_valid_func_name():
    return lambda name: not name.startswith("invalid")


@pytest.mark.parametrize("bad_prompt", BAD_PROMPTS)
def test_fewshot_prompt_fails_with_bad_prompt(bad_prompt, is_valid_func_name):
    with pytest.raises(ValueError):
        utils._validate_few_shot_prompt(
            str(bad_prompt),
            conversational=isinstance(bad_prompt, ConversationalPrompt),
            is_valid_func_name=is_valid_func_name,
        )


GOOD_PROMPTS = [
    """Q: Who is the president?
Ask Agent[search]: Who is the president?
Agent[search] says: It's Joe Biden.
A: It's Joe Biden.""",
    """Q: How many books are there in the library?
Ask Func[library]: How many books are there in the library?
Func[library] says: None
A: I don't know.""",
    """Q: How many books are there in the library?
Func[library] says: Many
A: There are many books in the library""",
    """Q: What is 12 + 15?
Agent[calc] says: 27
A: It's 27.""",
    """Q: What is the life expectancy in the US?
A: I think it's 80 years but I'm not sure.""",
    """Q: Replace the background in #image1 with a beautiful sunset
Ask Agent[mask2former]: Mask out the background in #image1
Agent[mask2former] says: I have masked out the selected region: #mask1
Ask Func[edit]: A beautiful sunset #image1 #mask1
Func[edit] says: Here you go: #image2
A: I replaced the background with a beautiful sunset: #image2""",
    ConversationalPrompt(
        """Q: Think of your favorite color
A: Okay, I'm thinking of it.
Q: Is it red?
A: No, it's not red.
Q: Is it blue?
A: Yes, it's blue!"""
    ),
    """Q: Who is tweeting with the fixie hashtag?
Ask Func[hashtag_search]: ##fixie
Func[hashtag_search] says: @fixie
A: @fixie is currently tweeting with the fixie hashtag""",
]


@pytest.mark.parametrize("good_prompt", GOOD_PROMPTS)
def test_fewshot_prompt_succeeds_with_good_prompt(good_prompt, is_valid_func_name):
    utils._validate_few_shot_prompt(
        str(good_prompt),
        conversational=isinstance(good_prompt, ConversationalPrompt),
        is_valid_func_name=is_valid_func_name,
    )
