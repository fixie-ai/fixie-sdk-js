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
Ask Func[schedule]:
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
Ask Func[time_in_seattle]:
Func[time_in_seattle] says: 10:25 AM
A: The next ferry leaving Edmonds is 11:05 AM.

Q: When does the next ferry leave Kingston?
Ask Func[schedule]:
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
Ask Func[time_in_seattle]:
Func[time_in_seattle] says: 4:37 PM
A: The next ferry leaving Kingston is 4:40 PM.

Q: When does the next ferry leave Kingston after 5:00p?
Ask Func[schedule]:
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
A: The next ferry leaving Kingston is 5:30 PM.

Q: When does the next ferry leave Edmonds after 7:25 AM?
Ask Func[schedule]:
Func[schedule] says: '\n\t\t\tLeave Edmonds (Daily)\n\t\t\n\t\t\t  5:35 1 11:55 1  6:15 111:45 1\n\t\t\n\t\t\t  6:10 2 12:40 2  7:00 2 \n\t\t\n\t\t\t  7:10 1  1:35 1  7:40 1 \n\t\t\n\t\t\t  7:55 2  2:25 2  8:30 2 \n\t\t\n\t\t\t  8:50 1  3:15 1  9:05 1 \n\t\t\n\t\t\t  9:35 2  3:55 2  9:50 2  \n\t\t\n\t\t\t10:20 1  4:45 110:25 1 \n\t\t\n\t\t\t11:05 2  5:25 211:10 2  \n\t\t\n\t\t\tLeave Kingston (Daily)\n\t\t\n\t\t\t  4:45 1 11:05 1  5:30 111:10 1\n\t\t\n\t\t\t  5:30 2 11:55 2  6:10 2 \n\t\t\n\t\t\t  6:25 112:45 1  7:00 1 \n\t\t\n\t\t\t  7:00 2  1:30 2  7:45 2 \n\t\t\n\t\t\t  7:55 1  2:30 1  8:20 1 \n\t\t\n\t\t\t  8:40 2  3:10 2  9:10 2  \n\t\t\n\t\t\t  9:35 1  4:00 1  9:40 1 \n\t\t\n\t\t\t10:20 2  4:40 210:30 2  \n\t\t\n\t'
A: The next ferry leaving Edmonds is 7:55 AM.
`;

export function time_in_seattle(query: { text: string; }): string {
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

export async function schedule() {
  const url = "https://wsdot.com/ferries/schedule/scheduledetailbyroute.aspx?route=ed-king";
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

