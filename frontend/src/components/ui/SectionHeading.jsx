export default function SectionHeading({ number, title, description, trailing }) {
  return (
    <div className="section-heading">
      <span className="step-number">{number}</span>
      <div><h2>{title}</h2><p>{description}</p></div>
      {trailing}
    </div>
  );
}
