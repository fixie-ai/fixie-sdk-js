#!/usr/bin/env python3

# This is an example Fixie Agent replies with each message in upper case.

import fixieai

agent = fixieai.StandaloneAgent(lambda query: query.text.upper())

if __name__ == "__main__":
    agent.serve()
