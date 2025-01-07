import React from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material';
import { Delete, Add } from '@mui/icons-material';

interface Rule {
  id: number;
  condition: string;
  action: string;
}

const RuleEditor: React.FC = () => {
  const [rules, setRules] = React.useState<Rule[]>([]);
  const [newRule, setNewRule] = React.useState({
    condition: '',
    action: '',
  });

  const handleAddRule = () => {
    if (newRule.condition && newRule.action) {
      setRules([
        ...rules,
        {
          id: Date.now(),
          condition: newRule.condition,
          action: newRule.action,
        },
      ]);
      setNewRule({ condition: '', action: '' });
    }
  };

  const handleDeleteRule = (id: number) => {
    setRules(rules.filter(rule => rule.id !== id));
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Custom Ontology Rules
      </Typography>

      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          label="Condition"
          value={newRule.condition}
          onChange={(e) => setNewRule({ ...newRule, condition: e.target.value })}
          sx={{ mb: 1 }}
        />
        <TextField
          fullWidth
          label="Action"
          value={newRule.action}
          onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
          sx={{ mb: 1 }}
        />
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddRule}
        >
          Add Rule
        </Button>
      </Box>

      <List>
        {rules.map((rule) => (
          <ListItem key={rule.id}>
            <ListItemText
              primary={rule.condition}
              secondary={rule.action}
            />
            <ListItemSecondaryAction>
              <IconButton onClick={() => handleDeleteRule(rule.id)}>
                <Delete />
              </IconButton>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default RuleEditor;
