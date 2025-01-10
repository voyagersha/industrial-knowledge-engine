import React from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
} from '@mui/material';
import { Delete, Check } from '@mui/icons-material';
import { validateOntology } from '../services/api';

interface OntologyValidatorProps {
  ontology: {
    entities: [string, string][];
    relationships: {
      source: string;
      target: string;
      type: string;
    }[];
  };
  onValidated: (graph: any) => void;
}

const OntologyValidator: React.FC<OntologyValidatorProps> = ({
  ontology,
  onValidated,
}) => {
  const [validatedOntology, setValidatedOntology] = React.useState(ontology);

  const handleDelete = (type: string, index: number) => {
    const updated = { ...validatedOntology };
    updated[type] = updated[type].filter((_: any, i: number) => i !== index);
    setValidatedOntology(updated);
  };

  const handleValidate = async () => {
    try {
      const result = await validateOntology(validatedOntology);
      onValidated(result.graph);
    } catch (error) {
      console.error('Error validating ontology:', error);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Validate Extracted Ontology
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Entities</Typography>
        <List>
          {validatedOntology.entities.map((entity: any, index: number) => (
            <ListItem key={index}>
              <ListItemText 
                primary={entity[0]}
                secondary={`Type: ${entity[1]}`}
              />
              <ListItemSecondaryAction>
                <IconButton onClick={() => handleDelete('entities', index)}>
                  <Delete />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Relationships</Typography>
        <List>
          {validatedOntology.relationships.map((rel: any, index: number) => (
            <ListItem key={index}>
              <ListItemText 
                primary={`${rel.source} → ${rel.target}`}
                secondary={`Type: ${rel.type}`}
              />
              <ListItemSecondaryAction>
                <IconButton onClick={() => handleDelete('relationships', index)}>
                  <Delete />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>

      <Button
        variant="contained"
        color="primary"
        onClick={handleValidate}
        startIcon={<Check />}
      >
        Confirm and Generate Graph
      </Button>
    </Box>
  );
};

export default OntologyValidator;