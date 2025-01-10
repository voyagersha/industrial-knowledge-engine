import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RuleEditor from '../RuleEditor';

describe('RuleEditor Component', () => {
  beforeEach(() => {
    render(<RuleEditor />);
  });

  it('renders without crashing', () => {
    expect(screen.getByText('Custom Ontology Rules')).toBeInTheDocument();
  });

  it('shows empty form inputs initially', () => {
    expect(screen.getByLabelText('Condition')).toHaveValue('');
    expect(screen.getByLabelText('Action')).toHaveValue('');
  });

  it('allows adding a new rule', async () => {
    const conditionInput = screen.getByLabelText('Condition');
    const actionInput = screen.getByLabelText('Action');
    const addButton = screen.getByText('Add Rule');

    await userEvent.type(conditionInput, 'test condition');
    await userEvent.type(actionInput, 'test action');
    fireEvent.click(addButton);

    expect(screen.getByText('test condition')).toBeInTheDocument();
    expect(screen.getByText('test action')).toBeInTheDocument();
  });

  it('allows deleting a rule', async () => {
    // Add a rule first
    const conditionInput = screen.getByLabelText('Condition');
    const actionInput = screen.getByLabelText('Action');
    const addButton = screen.getByText('Add Rule');

    await userEvent.type(conditionInput, 'test condition');
    await userEvent.type(actionInput, 'test action');
    fireEvent.click(addButton);

    // Now delete it
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteButton);

    expect(screen.queryByText('test condition')).not.toBeInTheDocument();
    expect(screen.queryByText('test action')).not.toBeInTheDocument();
  });
});
