/** This is a simple Node client for Fixie. */

import { FixieClient } from 'fixie';

const client = new FixieClient({ apiKey: process.env.FIXIE_API_KEY });
const user = await client.userInfo();
console.log(`You are authenticated to Fixie as: ${user.email}`);
