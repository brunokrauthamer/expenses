export function isTrustedGoogleAuthMessage(event, { origin, popup, requestId }) {
  const data = event?.data;
  return (
    event?.origin === origin &&
    event?.source === popup &&
    data?.type === 'expenses:google-auth' &&
    data?.requestId === requestId &&
    typeof data.success === 'boolean'
  );
}
