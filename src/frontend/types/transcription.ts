export type SummaryData = {
  item: string;
  "sub-item": string;
  descricao: string;
  peso: number;
  justificativa: string;
};

export type Transcription = {
  id: string;
  filename: string;
  content: string;
  classification: string;
  successfulCall: string;
  identifiedClient: string;
  summaryData: SummaryData[];
  improvementSugestion: string;
};