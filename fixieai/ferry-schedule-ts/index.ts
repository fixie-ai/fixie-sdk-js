// TODO: Move this to `fixie-examples/agents/template.ts` when we're ready.
/**
 * A templated Fixie agent
 *
 * Fixie docs:
 *     https://docs.fixie.ai
 *
 * Fixie agent example:
 *     https://github.com/fixie-ai/fixie-examples
 */

import axios from 'axios';
import * as cheerio from 'cheerio';

export const BASE_PROMPT = "I am an agent that looks up ferry schedules.";

export const FEW_SHOTS = `
Q: When does the next ferry leave Edmonds?
Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
Ask Func[timeInSeattle]:
Func[timeInSeattle] says: 10:25 AM
A: The next ferry leaving Edmonds is 11:05 AM.

Q: When does the next ferry leave Kingston?
Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
Ask Func[timeInSeattle]:
Func[timeInSeattle] says: 4:37 PM
A: The next ferry leaving Kingston is 4:40 PM.

Q: When does the next ferry leave Kingston after 5:00p?
Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
A: The next ferry leaving Kingston is 5:30 PM.

Q: When does the next ferry leave Edmonds after 7:25 AM?
Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
A: The next ferry leaving Edmonds is 7:55 AM.

Q: What are my ferry options?
Ask Func[timeInSeattle]:
Func[timeInSeattle] says: 12:01 PM
Ask Func[getTimesToTerminals]: 
Func[getTimesToTerminals] says: { "destination_addresses" : [ "801 WA-519, Seattle, WA 98104, USA", "264 Railroad Ave, Edmonds, WA 98020, USA" ], "origin_addresses" : [ "8026 15th Ave NW, Seattle, WA 98117, USA" ], "rows" : [ { "elements" : [ { "distance" : { "text" : "7.4 mi", "value" : 11877 }, "duration" : { "text" : "43 mins", "value" : 2608 }, "status" : "OK" }, { "distance" : { "text" : "9.9 mi", "value" : 15877 }, "duration" : { "text" : "24 mins", "value" : 1445 }, "status" : "OK" } ] } ], "status" : "OK" }

Thought: it'll take the user 43 minutes to get to the Seattle ferry terminal and 24 minutes to get to the Edmonds ferry terminal. It's currently 12:01p, so the user could get to the Seattle ferry terminal by 12:44p and the Edmonds ferry terminal by 12:25p.

Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'

Ask Func[schedule]: seattle
Func[schedule] says: Leave Seattle (Monday through Friday)   5:30 111:25 2  5:45 112:15 1   6:10 212:25 1  6:30 2  1:35 1   7:05 1  1:10 2  7:30 1    7:55 2  2:05 1  8:15 2    8:45 1  3:00 2  9:20 1    9:35 2  3:50 110:05 2  10:40 1  4:45 210:50 1  Leave Bainbridge Island (Monday through Friday)   4:45 110:25 2  4:45 111:30 1   5:20 211:30 1  5:35 212:55 1   6:20 112:20 2  6:40 1    7:05 2  1:15 1  7:20 2    7:55 1  2:05 2  8:20 1    8:45 2  2:55 1  9:00 2    9:40 1  3:50 210:00 1  Leave Seattle (Saturday, Sunday and Holidays)   6:10 1  1:15 1  7:20 2  2:10 1   7:55 1  2:10 2  8:10 1    8:55 2  3:05 1  9:00 2    9:35 1  3:50 2  9:45 1  10:40 2  4:45 110:40 2  11:25 1  5:35 211:15 1  12:30 2  6:25 112:45 1  Leave Bainbridge Island (Saturday, Sunday and Holidays)   5:20 112:20 1  6:30 2  1:25 1   7:05 1  1:20 2  7:15 1    7:55 2   2:10 1  8:10 2    8:45 1  3:00 2  8:55 1    9:45 2  3:55 1  9:45 2  10:25 1  4:40 210:30 1  11:35 2  5:35 1Midnight   1

A: You can take the 1:10p from Seattle or the 12:40p from Edmonds.

Q: What are my ferry options?
Ask Func[timeInSeattle]:
Func[timeInSeattle] says: 9:37am
Ask Func[getTimesToTerminals]: 
Func[getTimesToTerminals] says: { "destination_addresses" : [ "801 WA-519, Seattle, WA 98104, USA", "264 Railroad Ave, Edmonds, WA 98020, USA" ], "origin_addresses" : [ "8026 15th Ave NW, Seattle, WA 98117, USA" ], "rows" : [ { "elements" : [ { "distance" : { "text" : "7.4 mi", "value" : 11877 }, "duration" : { "text" : "43 mins", "value" : 2608 }, "status" : "OK" }, { "distance" : { "text" : "9.9 mi", "value" : 15877 }, "duration" : { "text" : "24 mins", "value" : 1445 }, "status" : "OK" } ] } ], "status" : "OK" }

Thought: it'll take the user 43 minutes to get to the Seattle ferry terminal and 24 minutes to get to the Edmonds ferry terminal. It's currently 9:37am, so the user could get to the Seattle ferry terminal by 10:20am or the Edmonds ferry terminal by 10:01am.

Ask Func[schedule]: edmonds
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'

Ask Func[schedule]: seattle
Func[schedule] says: Leave Seattle (Monday through Friday)   5:30 111:25 2  5:45 112:15 1   6:10 212:25 1  6:30 2  1:35 1   7:05 1  1:10 2  7:30 1    7:55 2  2:05 1  8:15 2    8:45 1  3:00 2  9:20 1    9:35 2  3:50 110:05 2  10:40 1  4:45 210:50 1  Leave Bainbridge Island (Monday through Friday)   4:45 110:25 2  4:45 111:30 1   5:20 211:30 1  5:35 212:55 1   6:20 112:20 2  6:40 1    7:05 2  1:15 1  7:20 2    7:55 1  2:05 2  8:20 1    8:45 2  2:55 1  9:00 2    9:40 1  3:50 210:00 1  Leave Seattle (Saturday, Sunday and Holidays)   6:10 1  1:15 1  7:20 2  2:10 1   7:55 1  2:10 2  8:10 1    8:55 2  3:05 1  9:00 2    9:35 1  3:50 2  9:45 1  10:40 2  4:45 110:40 2  11:25 1  5:35 211:15 1  12:30 2  6:25 112:45 1  Leave Bainbridge Island (Saturday, Sunday and Holidays)   5:20 112:20 1  6:30 2  1:25 1   7:05 1  1:20 2  7:15 1    7:55 2   2:10 1  8:10 2    8:45 1  3:00 2  8:55 1    9:45 2  3:55 1  9:45 2  10:25 1  4:40 210:30 1  11:35 2  5:35 1Midnight   1

A: You can take the 10:40am from Seattle or the 10:20am from Edmonds.
`;

export function timeInSeattle(query: { text: string; }): string {
  const seattleTimeZone = 'America/Los_Angeles';
  const options = {
    timeZone: seattleTimeZone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  } as const;

  const currentTimeSeattle = new Intl.DateTimeFormat('en-US', options).format(new Date());
  return currentTimeSeattle;
}

export async function schedule(query: {text: string}): Promise<string> {
  const route = query.text === 'edmonds' ? 'ed-king' : 'sea-bi';
  const url = `https://wsdot.com/ferries/schedule/scheduledetailbyroute.aspx?route=${route}`;
  const response = await axios.get(url);
  const htmlContent = response.data;

  const $ = cheerio.load(htmlContent);
  const element = $("#cphPageTemplate_rprSailings_gvSailing_0");

  if (element.length) {
    return element.text();
  } else {
    return 'Unexpected HTML structure';
  }
}

export async function getTimesToTerminals() {
  const url = `https://maps.googleapis.com/maps/api/distancematrix/json?destinations=47.6023189,-122.3404184|47.8104375,-122.3855401&origins=47.6876391,-122.37665&units=imperial&key=${process.env.GOOGLE_API_KEY}`;
  const response = await axios.get(url);
  return response.data;
}
