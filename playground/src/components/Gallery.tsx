import { useMemo } from 'react';

export interface Example {
  id: string;
  name: string;
  category: string;
  source: string;
  expectedOutput: string;
  version: string;
}

interface GalleryProps {
  examples: Example[];
  selectedId: string | null;
  onSelect: (example: Example) => void;
  onNew: () => void;
}

export function Gallery({ examples, selectedId, onSelect, onNew }: GalleryProps) {
  // Group examples by category
  const categorized = useMemo(() => {
    const groups: Record<string, Example[]> = {};
    for (const example of examples) {
      if (!groups[example.category]) {
        groups[example.category] = [];
      }
      groups[example.category].push(example);
    }
    return groups;
  }, [examples]);

  const categoryOrder = [
    'Basics',
    'Arrays',
    'Functions',
    'Data Structures',
    'Algorithms',
    'Math',
    'Strings',
    'JSON & Regex',
    'Other',
  ];

  const sortedCategories = Object.keys(categorized).sort(
    (a, b) => categoryOrder.indexOf(a) - categoryOrder.indexOf(b)
  );

  return (
    <div className="sidebar">
      <div className="sidebar-header">Examples</div>
      <div className="example-list">
        {/* New file button */}
        <button
          className={`example-item new-file ${selectedId === null ? 'active' : ''}`}
          onClick={onNew}
        >
          + New Program
        </button>
        <div className="example-divider" />

        {sortedCategories.map(category => (
          <div key={category} className="example-category">
            <div className="example-category-title">{category}</div>
            {categorized[category].map(example => (
              <button
                key={example.id}
                className={`example-item ${selectedId === example.id ? 'active' : ''}`}
                onClick={() => onSelect(example)}
              >
                {example.name}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
