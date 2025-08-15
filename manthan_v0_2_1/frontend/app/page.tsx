import AgentButton from "@/components/AgentButton";
import AgentHealthCard from "@/components/AgentHealthCard";

export default function Page() {
  const idea = {
    title: "Monsoon Chronicles",
    logline: "A young journalist uncovers a political scandal during a record monsoon in Mumbai, forcing a choice between truth and survival.",
    genre: "Thriller",
    tone: "Gritty"
  };

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Creator Suite — Guided Path</h1>
      <AgentHealthCard />
      <AgentButton idea={idea} />
    </main>
  );
}
