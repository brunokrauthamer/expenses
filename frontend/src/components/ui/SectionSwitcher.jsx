export default function SectionSwitcher({ label, value, options, onChange }) {
  return (
    <div className="section-switcher" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          type="button"
          key={option.value}
          aria-pressed={value === option.value}
          aria-controls={option.controls}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
