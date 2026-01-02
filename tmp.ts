import { Hono } from "hono";

const app = new Hono();

const sendReminder = async () => {
  try {
    const response = await fetch(
      `https://${Bun.env.BOT_DOMAIN}/reminder/send`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${Bun.env.SENDER_TOKEN}`,
          "Content-Type": "application/json",
        },
      },
    );

    const rawInfo = await response.text();

    let jsonObject: object;
    let executionDetails: string;

    try {
      jsonObject = rawInfo ? JSON.parse(rawInfo) : null;
      executionDetails = JSON.stringify(jsonObject, null, 2);
    } catch {
      executionDetails = rawInfo;
    }

    if (response.ok) {
      console.info("Sender request succeeded");
      console.info(`${executionDetails}`);
    } else {
      console.error("Sender request failed");
      console.error(`Status: ${response.status}`);
      console.error(`${executionDetails}`);
    }
  } catch (err) {
    console.error(`Error while sending reminder: ${err}`);
  }
};

await sendReminder();
