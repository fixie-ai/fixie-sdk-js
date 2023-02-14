# Fixie

Fixie is a platform for building applications using Large Language
Models. With Fixie, you can write apps that communicate, in natural
language, with one or more *agents* that can access individual APIs or
sources of data, such as GitHub, Google Calendar, or a database.

You can access the Fixie web interface at [app.fixie.ai](https://app.fixie.ai).
Using the Fixie SDK allows you to connect your own
applications to the Fixie platform, either as a client, or by
building custom agents that plug into the platform.

---

# Getting started

Install the Fixie SDK using pip:

```shell
$ pip install fixieai
```

Now, let's get started:

```pycon
>>> import fixieai
>>> client = fixieai.FixieClient()
```

