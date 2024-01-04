import twilio from 'twilio';
import express from 'express';
import bodyParser from 'body-parser';
import { FixieClient } from 'fixie';
import * as dotenv from 'dotenv';

const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_FROM_NUMBER = process.env.TWILIO_FROM_NUMBER;
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const INCOMING_ROUTE = process.env.INCOMING_ROUTE;
const EXPRESS_PORT = process.env.EXPRESS_PORT;
const FIXIE_AGENT_ID = process.env.FIXIE_AGENT_ID;
const FIXIE_API_KEY = process.env.FIXIE_API_KEY;

const USE_STREAMING = true; // Set to false to turn off streaming
const fixieClient = new FixieClient(FIXIE_API_KEY);

dotenv.config();
const { urlencoded } = bodyParser;
const app = express();
app.use(urlencoded({ extended: false }));

app.post(INCOMING_ROUTE, (request, response) => {
  const twilioSignature = request.header('X-Twilio-Signature');
  const validTwilioRequest = twilio.validateRequest(
    TWILIO_AUTH_TOKEN,
    twilioSignature,
    new URL(WEBHOOK_URL + INCOMING_ROUTE),
    request.body
  );

  if (validTwilioRequest) {
    let incomingMessageText = request.body.Body;
    let fromNumber = request.body.From;

    console.log(`Got an SMS message. From: ${fromNumber} Message: ${incomingMessageText}`);
    fixieClient;

    // Start a conversation with our agent
    fixieClient
      .startConversation({ agentId: FIXIE_AGENT_ID, message: incomingMessageText, stream: USE_STREAMING })
      .then((conversation) => {
        const reader = conversation.getReader();

        // this will hold any 'done' assistant messages along the way
        let agentMsg = [];

        reader.read().then(function processAgentMessage({ done, value }) {
          if (done) {
            console.log('Done reading agent messages');
            response.status(200).end();
            return;
          }

          // --------------------------------------------------------------------------------------------
          // -- STREAMING EXAMPLE
          // --------------------------------------------------------------------------------------------
          // -- This example uses streaming. This is so we can immediately send back the first message
          // -- (e.g. "Let me check on that"). We ignore messages that are not "done" and then send the
          // -- final response back to the user.
          // -- If you want to not use streaming, comment out this section and uncomment the next section.
          // --------------------------------------------------------------------------------------------

          // Process each message we get back from the agent
          // Get the turns and see if there are any assistant messages that are done
          value.turns.forEach((turn) => {
            // It's an assistant turn
            if (turn.role == 'assistant') {
              // See if there are messages that are done
              turn.messages.forEach((message) => {
                // We have one -- if we haven't seen it before, log it
                if (message.state == 'done') {
                  let currentMsg = { turnId: turn.id, timestamp: turn.timestamp, content: message.content };
                  if (!agentMsg.some((msg) => JSON.stringify(msg) === JSON.stringify(currentMsg))) {
                    agentMsg.push(currentMsg);
                    sendSmsMessage(fromNumber, message.content);
                    console.log(
                      `Turn ID: ${turn.id}. Timestamp: ${turn.timestamp}. Assistant says: ${message.content}`
                    );
                  }
                }
              });
            }
          });

          // --------------------------------------------------------------------------------------------
          // -- NON-STREAMING EXAMPLE
          // --------------------------------------------------------------------------------------------
          // -- Turns off streaming. Just iterate through the messages and send back to user.
          // -- This sends back two messages (e.g."Let me check on that" and then the final response).
          // -- Messages typically sent very close together so you may want to suppress the first one.
          // --------------------------------------------------------------------------------------------
          // if(value.role == "assistant") {
          //   value.messages.forEach(message => {
          //     if(message.kind == "text" && message.state == "done") {
          //       sendSmsMessage(fromNumber, message.content);
          //     }
          //   });
          // }

          // Read next agent message
          reader.read().then(processAgentMessage);
        });
      });
  } else {
    console.log('[Danger] Potentially spoofed message. Silently dropping it...');
    response.sendStatus(403);
  }
});

app.listen(EXPRESS_PORT, () => {
  console.log(`listening on port ${EXPRESS_PORT}.`);
});

function sendSmsMessage(to, body) {
  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
  console.log(`Sending message to ${to}: ${body}`);
  return client.messages.create({
    body,
    to,
    from: TWILIO_FROM_NUMBER,
  });
}
