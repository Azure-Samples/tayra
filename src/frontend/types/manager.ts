import { Specialist } from "@/types/specialist";

export type Manager = {
  name: string;
  role: string;
  specialists: Specialist[];
  transcriptions: number;
  performance: number;
};