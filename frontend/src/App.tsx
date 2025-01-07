import React from 'react';
import { ThemeProvider, CssBaseline, Container, Box } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import FileUpload from './components/FileUpload';
import OntologyValidator from './components/OntologyValidator';
import GraphViewer from './components/GraphViewer';
import RuleEditor from './components/RuleEditor';
import ChatInterface from './components/ChatInterface';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
  },
});

const App: React.FC = () => {
  const [ontology, setOntology] = React.useState<any>(null);
  const [graph, setGraph] = React.useState<any>(null);
  const [currentStep, setCurrentStep] = React.useState<number>(0);

  const handleFileProcessed = (result: any) => {
    setOntology(result.ontology);
    setCurrentStep(1);
  };

  const handleOntologyValidated = (graph: any) => {
    setGraph(graph);
    setCurrentStep(2);
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          {currentStep === 0 && (
            <FileUpload onProcessed={handleFileProcessed} />
          )}
          {currentStep === 1 && (
            <OntologyValidator
              ontology={ontology}
              onValidated={handleOntologyValidated}
            />
          )}
          {currentStep === 2 && (
            <>
              <GraphViewer graph={graph} />
              <ChatInterface />
              <RuleEditor />
            </>
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
};

export default App;