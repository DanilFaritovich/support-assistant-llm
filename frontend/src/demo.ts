export interface DemoTicket {
  id: string;
  label: string;
  ticketText: string;
}

export const DEMO_TEMPLATE = `Summary:

Environment:

Steps to reproduce:

Actual result:

Expected result:

Additional information:`;

export const DEMO_TICKETS: DemoTicket[] = [
  {
    id: 'login',
    label: 'Sign-in problem',
    ticketText:
      'After entering a valid one-time code in the employee portal, the page shows “Session expired” and returns to the sign-in screen. The issue started this morning and affects two test accounts.',
  },
  {
    id: 'laptop',
    label: 'Laptop docking issue',
    ticketText:
      'A demo user’s laptop no longer detects either external monitor after reconnecting to the USB-C dock. The keyboard and network connection through the same dock still work.',
  },
  {
    id: 'deployment',
    label: 'Deployment unavailable',
    ticketText:
      'The staging deployment for the demo catalog service has been pending for 25 minutes. The deployment dashboard reports that no runner is available; the previous deployment completed successfully.',
  },
];
