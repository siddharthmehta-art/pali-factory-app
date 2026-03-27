import React, { useState } from 'react';
import { 
  LayoutDashboard, Package, Truck, FileText, 
  Layers, Database, Settings, Bell, Search 
} from 'lucide-react';

const SAPMasterPortal = () => {
  const [activeTab, setActiveTab] = useState('Dashboard');

  // 1. RAW MATERIAL STOCK DATA
  const rawMaterials = [
    { id: "RM-501", item: "Steel Rebars (12mm)", qty: "150 Tons", location: "Warehouse A", status: "In Stock" },
    { id: "RM-502", item: "Solar Grade Silicon", qty: "45 Cases", location: "Warehouse B", status: "Low Stock" },
  ];

  // 2. DEVELOPED STOCK (FINISHED GOODS)
  const developedStock = [
    { id: "FG-901", project: "Jalaun Solar Array", unit: "Panel Set Type-A", qty: "4,200 Units", value: "₹2.4Cr" },
    { id: "FG-902", project: "RDSS Smart Meter", unit: "Phase-1 Modules", qty: "12,000 Units", value: "₹85L" },
  ];

  return (
    <div className="flex h-screen bg-slate-100 font-sans overflow-hidden">
      
      {/* --- SIDEBAR (Restored Navigation) --- */}
      <div className="w-72 bg-[#1c222d] text-slate-300 flex flex-col shadow-xl">
        <div className="p-6 text-xl font-bold text-white border-b border-slate-700 flex items-center gap-2">
          <Database className="text-blue-400" /> ERP Central
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <p className="text-xs font-semibold text-slate-500 uppercase px-3 mb-2">Core Modules</p>
          <NavItem icon={<LayoutDashboard size={18}/>} label="Executive Dashboard" active={activeTab === 'Dashboard'} onClick={() => setActiveTab('Dashboard')} />
          <NavItem icon={<Layers size={18}/>} label="Developed Stock Report" active={activeTab === 'DevStock'} onClick={() => setActiveTab('DevStock')} />
          <NavItem icon={<Package size={18}/>} label="Raw Material Stock" active={activeTab === 'RawMaterial'} onClick={() => setActiveTab('RawMaterial')} />
          
          <p className="text-xs font-semibold text-slate-500 uppercase px-3 mt-6 mb-2">Reports & Analytics</p>
          <NavItem icon={<FileText size={18}/>} label="Solar Evacuation Reports" active={activeTab === 'Solar'} onClick={() => setActiveTab('Solar')} />
          <NavItem icon={<Truck size={18}/>} label="Logistics & RDSS" active={activeTab === 'Logistics'} onClick={() => setActiveTab('Logistics')} />
          <NavItem icon={<Settings size={18}/>} label="System Config" />
        </nav>
      </div>

      {/* --- MAIN CONTENT AREA --- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b flex items-center justify-between px-8">
          <div className="flex items-center bg-gray-100 px-3 py-1.5 rounded-md w-96">
            <Search size={16} className="text-gray-400 mr-2" />
            <input type="text" placeholder="Search Transactions, Materials..." className="bg-transparent outline-none text-sm w-full" />
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs text-gray-500">Welcome Back</p>
              <p className="text-sm font-bold text-gray-800">Admin User</p>
            </div>
            <div className="w-10 h-10 rounded bg-blue-600 text-white flex items-center justify-center font-bold">A</div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          
          {/* --- CONDITIONALLY RENDERED REPORTS --- */}
          
          {activeTab === 'DevStock' && (
            <div className="animate-in fade-in duration-500">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Developed Stock Report</h2>
              <TableLayout headers={["Batch ID", "Project Link", "Unit Description", "Quantity", "Inventory Value"]} data={developedStock} />
            </div>
          )}

          {activeTab === 'RawMaterial' && (
            <div className="animate-in fade-in duration-500">
              <h2 className="text-2xl font-bold text-gray-800 mb-6">Raw Material Inventory</h2>
              <TableLayout headers={["Material ID", "Item Name", "Current Qty", "Warehouse", "Status"]} data={rawMaterials} />
            </div>
          )}

          {activeTab === 'Dashboard' && (
            <div className="grid grid-cols-3 gap-6">
              <StatCard title="Total Stock Value" value="₹14.2 Cr" color="border-l-blue-500" />
              <StatCard title="Active RDSS Projects" value="12" color="border-l-green-500" />
              <StatCard title="Pending RM Orders" value="08" color="border-l-orange-500" />
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

// --- HELPER COMPONENTS (To keep it clean) ---
const NavItem = ({ icon, label, active, onClick }) => (
  <div 
    onClick={onClick}
    className={`flex items-center gap-3 p-3 rounded-md cursor-pointer transition-all ${active ? 'bg-blue-600 text-white shadow-lg' : 'hover:bg-slate-800 text-slate-400'}`}
  >
    {icon} <span className="text-sm font-medium">{label}</span>
  </div>
);

const StatCard = ({ title, value, color }) => (
  <div className={`bg-white p-6 rounded-lg shadow-sm border-l-4 ${color}`}>
    <p className="text-sm text-gray-500 mb-1">{title}</p>
    <p className="text-2xl font-bold text-gray-800">{value}</p>
  </div>
);

const TableLayout = ({ headers, data }) => (
  <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
    <table className="w-full text-left">
      <thead className="bg-gray-50 border-b">
        <tr>
          {headers.map(h => <th key={h} className="p-4 text-xs uppercase text-gray-500 font-bold">{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i} className="border-b hover:bg-slate-50">
            {Object.values(row).map((val, j) => <td key={j} className="p-4 text-sm text-gray-700">{val}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export default SAPMasterPortal;
