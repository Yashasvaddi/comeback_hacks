// Fixed engineering backdrop: faint dot-grid + a single restrained warm wash.
// Static (no blob animation) — reads as a designed technical surface, not a template.
export default function Backdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10">
      <div className="backdrop-grid absolute inset-0 opacity-70" />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(900px 500px at 88% -8%, rgba(232,131,58,0.10), transparent 60%), radial-gradient(700px 500px at -5% 105%, rgba(79,157,176,0.07), transparent 60%)",
        }}
      />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent,rgba(10,11,13,0.5))]" />
    </div>
  );
}
