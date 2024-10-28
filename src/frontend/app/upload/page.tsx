import React from "react";
import { Metadata } from "next";
import UploadFile from "@/components/UploadFile";
import DefaultLayout from "@/components/Layouts/DefaultLayout";
import TranscriptionJob from "@/components/ProcessTranscription";
import Breadcrumb from "@/components/Breadcrumbs/Breadcrumb";


export const metadata: Metadata = {
  title: "Processamento de Transcrições | TailAdmin - Next.js Dashboard Template",
  description:
    "Esta é a página de Processamento de Transcrições para o TailAdmin - Next.js Tailwind CSS Admin Dashboard Template",
};


const FormElementsPage = () => {
  return (
    <DefaultLayout>
      <Breadcrumb pageName={"Processamento de Transcrições"} />
      <div className="flex flex-col md:flex-row justify-between gap-6 p-6">
        <div className="flex-1">
          <UploadFile />
        </div>
        <div className="flex-1">
          <TranscriptionJob />
        </div>
      </div>
    </DefaultLayout>
  );
};

export default FormElementsPage;
