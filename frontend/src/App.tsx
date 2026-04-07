import "./App.css";
import { ArrowUpIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

function App() {
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 md:flex-row">
        <Button variant="outline">Button</Button>
        <Button variant="outline" size="icon" aria-label="Submit">
          <ArrowUpIcon />
        </Button>
      </div>
    </>
  );
}

export default App;
