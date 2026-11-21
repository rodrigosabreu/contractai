export function cn(...inputs: (string | undefined | null | false | Record<string, boolean>)[]): string {
  return inputs
    .flatMap((input) => {
      if (typeof input === 'string') return input;
      if (typeof input === 'object' && input !== null) {
        return Object.entries(input)
          .filter(([, value]) => value)
          .map(([key]) => key);
      }
      return [];
    })
    .join(' ');
}