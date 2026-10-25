const paths = {
  entry: (
    <>
      <path d="M12 5v14M5 12h14" />
    </>
  ),
  overview: (
    <>
      <path d="M4 19V5M4 19h16" />
      <path d="m7 14 4-4 3 2 5-6" />
    </>
  ),
  edit: (
    <>
      <path d="m15 5 4 4M4 20l4-.8L19 8a2.1 2.1 0 0 0-3-3L5 16l-1 4Z" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M10 11v6M14 11v6" />
      <path d="m6 7 1 13h10l1-13M9 7V4h6v3" />
    </>
  ),
  close: (
    <>
      <path d="m6 6 12 12M18 6 6 18" />
    </>
  ),
  search: (
    <>
      <circle cx="10.8" cy="10.8" r="6.3" />
      <path d="m16 16 4 4" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </>
  ),
  basket: (
    <>
      <path d="m4 10 2 10h12l2-10H4Z" />
      <path d="m8 10 4-7 4 7M8 14v3M12 14v3M16 14v3" />
    </>
  ),
  ticket: (
    <>
      <path d="M4 7a2 2 0 0 0 0 4v2a2 2 0 0 0 0 4h16a2 2 0 0 0 0-4v-2a2 2 0 0 0 0-4H4Z" />
      <path d="M13 8v2M13 14v2" />
    </>
  ),
  utensils: (
    <>
      <path d="M7 3v7M4 3v4a3 3 0 0 0 6 0V3M7 10v11M17 3v18M17 3c-2 2-3 5-3 8h6c0-3-1-6-3-8Z" />
    </>
  ),
  bus: (
    <>
      <path d="M5 16V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v10M5 11h14M7 16v3M17 16v3M5 19h14" />
      <circle cx="8" cy="14" r="1" />
      <circle cx="16" cy="14" r="1" />
    </>
  ),
  car: (
    <>
      <path d="m5 11 1.5-5h11L19 11l2 2v5h-3M6 18H3v-5l2-2M5 11h14M7 18h10" />
      <circle cx="7" cy="15" r="1" />
      <circle cx="17" cy="15" r="1" />
    </>
  ),
  gift: (
    <>
      <rect x="3" y="9" width="18" height="12" rx="2" />
      <path d="M12 9v12M3 13h18M12 9H7a2 2 0 1 1 2-2c0 2 3 2 3 2Zm0 0h5a2 2 0 1 0-2-2c0 2-3 2-3 2Z" />
    </>
  ),
  sparkles: (
    <>
      <path d="m12 3 1.4 5.6L19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3Z" />
      <path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15ZM5 3l.6 1.4L7 5l-1.4.6L5 7l-.6-1.4L3 5l1.4-.6L5 3Z" />
    </>
  ),
  wrench: (
    <>
      <path d="M14.5 6.5a5 5 0 0 0-6.8 6.8L3 18a2 2 0 0 0 3 3l4.7-4.7a5 5 0 0 0 6.8-6.8l-3 3-3-3 3-3Z" />
    </>
  ),
  heart: (
    <>
      <path d="M20.8 8.8c0 4.2-8.8 10-8.8 10s-8.8-5.8-8.8-10a4.7 4.7 0 0 1 8.8-2.3 4.7 4.7 0 0 1 8.8 2.3Z" />
      <path d="M8 12h2l1-2 2 4 1-2h2" />
    </>
  ),
  medical: (
    <>
      <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3Z" />
    </>
  ),
  plane: (
    <>
      <path d="m3 11 18-8-6 18-3-7-9-3Z" />
      <path d="m12 14 5-5" />
    </>
  ),
  receipt: (
    <>
      <path d="M5 3h14v18l-3-2-4 2-4-2-3 2V3Z" />
      <path d="M8 8h8M8 12h8M8 16h4" />
    </>
  ),
  home: (
    <>
      <path d="m3 11 9-8 9 8M5 10v11h14V10M9 21v-7h6v7" />
    </>
  ),
  sofa: (
    <>
      <path d="M4 12a2 2 0 0 1 4 0v2h8v-2a2 2 0 0 1 4 0v6H4v-6ZM6 18v3M18 18v3M8 14V9a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v5" />
    </>
  ),
  tag: (
    <>
      <path d="M20 13 13 20 3 10V4h6l11 9Z" />
      <circle cx="7.5" cy="7.5" r="1" />
    </>
  ),
  salary: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="12" cy="12" r="3" />
      <path d="M7 9h.01M17 15h.01M12 10v4m1.5-3c-.4-.5-.8-.5-1.5-.5-1.5 0-1.5 1.5 0 1.5s1.5 1.5 0 1.5c-.7 0-1.1-.1-1.5-.5" />
    </>
  ),
  wallet: (
    <>
      <path d="M4 6h15a2 2 0 0 1 2 2v11H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h13" />
      <path d="M16 12h5v4h-5a2 2 0 0 1 0-4Z" />
      <circle cx="16.5" cy="14" r=".5" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path
        d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.5.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.5-.9l-1.7.7-1.4-2.4L7.7 15a8 8 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.5-.9l.3-1.8H14l.3 1.8a8 8 0 0 1 1.5.9l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1-.1 1.8Z"
        transform="translate(-1 -1)"
      />
    </>
  ),
};

export default function Icon({ name, size = 18, strokeWidth = 1.8, ...props }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      {...props}
    >
      {paths[name] ?? null}
    </svg>
  );
}
