# Fixie.ai SDK Reference

[Fixie](https://fixie.ai) is a platform for building applications using Large Language
Models. With Fixie, you can write apps that communicate, in natural
language, with one or more *Agents* that can access individual APIs or
sources of data, such as GitHub, Google Calendar, or a database.

You can access the Fixie web interface at [app.fixie.ai](https://app.fixie.ai).
Using the Fixie SDK allows you to connect your own
applications to the Fixie platform, either as a client, or by
building custom agents that plug into the platform.

To learn more about Fixie, check us out at [https://fixie.ai](https://fixie.ai).

---

# Getting started

Install the Fixie SDK using pip:

```shell
$ pip install fixieai
```

Set your `FIXIE_API_KEY` environment variable to your API key, which
you can find in the Fixie web interface:
```shell
$ export FIXIE_API_KEY=<YOUR API KEY>
```

Now, import the Fixie SDK and use it to run queries:

```pycon
>>> import fixieai
>>> response = fixieai.query("How many GitHub issues are assigned to me?")
>>> print(response)
```

# Documentation

Check out the links on the left navigation bar for more information on how to
get started using Fixie.
