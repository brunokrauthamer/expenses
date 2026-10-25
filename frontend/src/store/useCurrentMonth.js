import { useEffect, useState } from 'react';
import { currentMonthISO } from '../shared/format.js';

function nextMonthStart() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth() + 1, 1).getTime();
}

export function useCurrentMonth() {
  const [month, setMonth] = useState(currentMonthISO);

  useEffect(() => {
    let timer;
    const refreshMonth = () => setMonth(currentMonthISO());
    const schedule = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(
        () => {
          refreshMonth();
          schedule();
        },
        Math.max(50, nextMonthStart() - Date.now() + 50),
      );
    };
    const onVisibilityChange = () => {
      if (!document.hidden) refreshMonth();
      schedule();
    };

    schedule();
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  return month;
}
