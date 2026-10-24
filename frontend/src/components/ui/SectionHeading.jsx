export default function SectionHeading({ number, title, description, trailing, titleId }) {
  return (
    <div className="section-heading">
      <span className="step-number">{number}</span>
      <div><h2 id={titleId}>{title}</h2><p>{description}</p></div>
      {trailing}
    </div>
  );
}
