import pytest

from fixieai.agents import utils

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
]


@pytest.mark.parametrize("bad_prompt", BAD_PROMPTS)
def test_fewshot_prompt_fails_with_bad_prompt(bad_prompt):
    with pytest.raises(ValueError):
        utils._validate_few_shot_prompt(bad_prompt)


GOOD_PROMPTS = [
    """Q: Who is the president?
Ask Agent[search]: Who is the president?
Agent[search] says: It's Joe Biden.
A: It's Joe Biden.""",
    # Ask Func without Func says
    """Q: How many books are there in the library?
Ask Func[library]: How many books are there in the library?
Func[library] says: None
A: I don't know.""",
    """Q: What is 12 + 15?
Agent[calc] says: 27
A: It's 27.""",
    """Q: What is the life expectancy in the US?
A: I think it's 80 years but I'm not sure.""",
    """Q: Replace the background in [image1] with a beautiful sunset
Ask Agent[mask2former]: Mask out the background in [image1]
Agent[mask2former] says: I have masked out the selected region: [mask1]
Ask Func[edit]: A beautiful sunset [image1] [mask1]
Func[edit] says: Here you go: [image2]
A: I replaced the background with a beautiful sunset: [image2]""",
]


@pytest.mark.parametrize("good_prompt", GOOD_PROMPTS)
def test_fewshot_prompt_succeeds_with_good_prompt(good_prompt):
    utils._validate_few_shot_prompt(good_prompt)
