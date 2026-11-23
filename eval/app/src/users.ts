export type Role = 'customer' | 'staff' | 'admin';

export interface User {
  id: string;
  name: string;
  role: Role;
}
