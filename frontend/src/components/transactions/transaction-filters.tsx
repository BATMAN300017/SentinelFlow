'use client';

import React from 'react';
import { FilterBar } from '@/components/shared/filter-bar';
import { CHANNELS } from '@/lib/constants';

interface TransactionFiltersProps {
  search: string;
  onSearchChange: (val: string) => void;
  channel: string;
  onChannelChange: (val: string) => void;
  minScore: string;
  onMinScoreChange: (val: string) => void;
  onReset: () => void;
}

export function TransactionFilters({
  search,
  onSearchChange,
  channel,
  onChannelChange,
  minScore,
  onMinScoreChange,
  onReset,
}: TransactionFiltersProps) {
  const channelOptions = [
    { label: 'All Channels', value: '' },
    ...CHANNELS.map((ch) => ({ label: ch, value: ch })),
  ];

  const riskOptions = [
    { label: 'All Risk Scores', value: '' },
    { label: 'Routine (0-24)', value: '0' },
    { label: 'Low (25+)', value: '25' },
    { label: 'Elevated (50+)', value: '50' },
    { label: 'High Priority (75+)', value: '75' },
  ];

  return (
    <FilterBar
      searchValue={search}
      onSearchChange={onSearchChange}
      searchPlaceholder="Search Account, Txn ID, or Beneficiary..."
      options={[
        {
          name: 'channel',
          value: channel,
          items: channelOptions,
          onChange: onChannelChange,
        },
        {
          name: 'risk',
          value: minScore,
          items: riskOptions,
          onChange: onMinScoreChange,
        },
      ]}
      onReset={onReset}
    />
  );
}
