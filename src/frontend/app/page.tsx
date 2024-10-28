import Breadcrumb from "@/components/Breadcrumbs/Breadcrumb";
import CardLayout from "@/components/Cards/Cards";

import { Metadata } from "next";
import DefaultLayout from "@/components/Layouts/DefaultLayout";

export const metadata: Metadata = {
  title: "Avaliação de Trascrições | Gerentes",
  description:
    "Avalie as transcrições dos gerentes e especialistas da sua equipe.",
};

const TablesPage = () => {
  return (
    <DefaultLayout>
      <Breadcrumb pageName="Avaliar Transcrições" />
      <div className="flex flex-col gap-10">
        <CardLayout />
      </div>
    </DefaultLayout>
  );
};

export default TablesPage;
