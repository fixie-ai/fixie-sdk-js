// Import the Fixie client
import { FixieClient } from 'fixie';
import 'dotenv/config';
import axios from 'axios';
import { encode } from 'gpt-3-encoder';

// Set the API key and Create the Fixie client
const FIXIE_API_KEY = process.env.FIXIE_API_KEY;

// Set our Agent ID that we want to get usage info on
const AGENT_ID = process.env.FIXIE_AGENT_ID;

// const fixieClient = new FixieClient({ apiKey: FIXIE_API_KEY });  // TODO once we have the right method

let numConversations = 0;
let numMessages = 0;
let lenConversations = 0;
let numTokens = 0;

console.log('calling listAgentConversations');
getAgentConversations(AGENT_ID).then((data) => {
  numConversations = data.length;

  console.log(`Got back ${data.length} conversations`);
  data.forEach((element) => {
    console.log('------------------------------------------------------------\n');
    console.log(`Conversation ID: ${element.id}`);
    console.log(`Total conversation turns\t${element.turns.length}`);

    getConvoTurns(element);

    // We want to get content for any messages that are:
    // conversation.role = "user" -> get messages that are messages.kind = "text" and get messages.content for the text of the message
    //      make sure the state is "done"
    // conversation.role = "assistant"
    //      kind = "text", get the content
    //      make sure the state is "done"
    //
    //      kind = "functionResponse"....get the response
  });

  console.log('\n\n============================================================');
  console.log(`Final stats for agent ${AGENT_ID}:\n`);
  console.log(`Total Conversations\t${numConversations}\n`);
  console.log(`Total Agent Messages\t${numMessages}\n`);
  console.log(`Total Characters\t${lenConversations}\n`);
  console.log(`Total LLM Tokens\t${numTokens}\n`);
  console.log('============================================================');
});

function getConvoTurns(conversation) {
  let numConvoMessages = 0;
  let numConvoChars = 0;
  let numConvoTokens = 0;

  // Iterate thru the conversation and process all the turns
  conversation.turns.forEach((turn) => {
    numConvoMessages += turn.messages.length;

    // Iterate through the turn messages and log their stats
    turn.messages.forEach((message) => {
      // console.log(message);
      numMessages++;
      // Make sure it's a message type that we want
      if (turn.state == 'done') {
        // Function Response
        if (turn.role == 'assistant' && message.kind == 'functionResponse') {
          lenConversations += message.response.length;
          const encoded = encode(message.response);
          numTokens += encoded.length;

          numConvoChars += message.response.length;
          numConvoTokens += encoded.length;
        } else if (message.kind == 'text' && (turn.role == 'assistant' || turn.role == 'user')) {
          lenConversations += message.content.length;
          const encoded = encode(message.content);
          numTokens += encoded.length;

          numConvoChars += message.content.length;
          numConvoTokens += encoded.length;
        }
      }
    });
  });

  console.log(`Total conversation messages\t${numConvoMessages}`);
  console.log(`Total conversation characters\t${numConvoChars}`);
  console.log(`Total conversation tokens\t${numConvoTokens}`);
}

async function getAgentConversations(agentId) {
  try {
    const response = await axios({
      method: 'get',
      maxBodyLength: Infinity,
      url: `https://api.fixie.ai/api/v1/agents/${agentId}/conversations`,
      headers: {
        Authorization: `Bearer ${FIXIE_API_KEY}`,
      },
    });
    // console.log(response.data.conversations);
    return response.data.conversations;
  } catch (error) {
    console.log(error);
  }
}
