import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../api/client';
import { DocumentItem } from '../types';
import {
  FileText, Upload, Plus, Trash2, Shield, Eye,
  AlertCircle, CheckCircle2, Clock, X
} from 'lucide-react';

export const Documents: React.FC = () => {
  const queryClient = useQueryClient();
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [aclDocId, setAclDocId] = useState<string | null>(null);

  // Paste form state
  const [pasteTitle, setPasteTitle] = useState('');
  const [pasteDept, setPasteDept] = useState('HR');
  const [pasteText, setPasteText] = useState('');
  const [pastePrincipals, setPastePrincipals] = useState('general_employee');

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDept, setUploadDept] = useState('Engineering');
  const [uploadPrincipals, setUploadPrincipals] = useState('general_employee');

  // ACL edit state
  const [aclInput, setAclInput] = useState('');

  const [formError, setFormError] = useState<string | null>(null);

  const { data: documents, isLoading } = useQuery<DocumentItem[]>({
    queryKey: ['documents'],
    queryFn: () => apiFetch<DocumentItem[]>('/api/documents?include_deleted=true'),
  });

  const { data: docDetail } = useQuery<DocumentItem>({
    queryKey: ['document', selectedDocId],
    queryFn: () => apiFetch<DocumentItem>(`/api/documents/${selectedDocId}`),
    enabled: !!selectedDocId,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/documents/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err: any) => alert(err.message),
  });

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      const principalsList = pastePrincipals.split(',').map(s => s.trim()).filter(Boolean);
      await apiFetch('/api/documents/paste', {
        method: 'POST',
        body: JSON.stringify({
          title: pasteTitle,
          department: pasteDept,
          raw_text: pasteText,
          permitted_principals: principalsList,
        }),
      });
      setShowPasteModal(false);
      setPasteTitle('');
      setPasteText('');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err: any) {
      setFormError(err.message);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setFormError(null);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('title', uploadTitle || uploadFile.name);
      formData.append('department', uploadDept);
      formData.append('permitted_principals', uploadPrincipals);

      await apiFetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadTitle('');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err: any) {
      setFormError(err.message);
    }
  };

  const handleAclUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aclDocId) return;
    try {
      const principalsList = aclInput.split(',').map(s => s.trim()).filter(Boolean);
      await apiFetch(`/api/documents/${aclDocId}/acls`, {
        method: 'PUT',
        body: JSON.stringify({ permitted_principals: principalsList }),
      });
      setAclDocId(null);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Documents & Access Control</h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative documents, vector indexing status, and principal-based access control.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => { setShowPasteModal(true); setFormError(null); }}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Paste Text Document</span>
          </button>
          <button
            onClick={() => { setShowUploadModal(true); setFormError(null); }}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span>Upload File (PDF/TXT/MD)</span>
          </button>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-slate-400">Loading documents...</div>
        ) : !documents || documents.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No documents uploaded yet. Upload or paste a document to begin.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3">Document Title</th>
                  <th className="px-6 py-3">Department</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Permitted Principals</th>
                  <th className="px-6 py-3">Version / ACL Epoch</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {documents.map((d) => (
                  <tr key={d.id} className={`hover:bg-slate-50/80 ${d.is_tombstoned ? 'bg-red-50/30' : ''}`}>
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <FileText className={`w-4 h-4 ${d.is_tombstoned ? 'text-red-400' : 'text-brand-600'}`} />
                        <span className={d.is_tombstoned ? 'line-through text-slate-500' : ''}>
                          {d.title}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-700">{d.department}</td>
                    <td className="px-6 py-4">
                      {d.is_tombstoned ? (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-red-100 text-red-800">
                          Tombstoned (Deleted)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800">
                          {d.indexing_status.toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-[11px]">
                      {d.is_tombstoned ? (
                        <span className="text-slate-400 italic">None (Access blocked)</span>
                      ) : (
                        d.permitted_principals.join(', ') || 'None'
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      v{d.content_version} / epoch {d.acl_epoch}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        onClick={() => setSelectedDocId(d.id)}
                        className="p-1 text-slate-500 hover:text-brand-600 rounded"
                        title="View Document"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      {!d.is_tombstoned && (
                        <>
                          <button
                            onClick={() => {
                              setAclDocId(d.id);
                              setAclInput(d.permitted_principals.join(', '));
                            }}
                            className="p-1 text-slate-500 hover:text-purple-600 rounded"
                            title="Edit Permissions"
                          >
                            <Shield className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`Permanently delete and purge "${d.title}"?`)) {
                                deleteMutation.mutate(d.id);
                              }
                            }}
                            className="p-1 text-slate-500 hover:text-red-600 rounded"
                            title="Delete Document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Paste Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-base">Paste Text Document</h3>
              <button onClick={() => setShowPasteModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">{formError}</div>
            )}

            <form onSubmit={handlePasteSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={pasteTitle}
                  onChange={(e) => setPasteTitle(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="e.g. Q4 Executive Bonus Schedule"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Department</label>
                <select
                  value={pasteDept}
                  onChange={(e) => setPasteDept(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="HR">HR</option>
                  <option value="Finance">Finance</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Operations">Operations</option>
                  <option value="General">General</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Permitted Principals (comma-separated)</label>
                <input
                  type="text"
                  value={pastePrincipals}
                  onChange={(e) => setPastePrincipals(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="general_employee, hr_manager"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Content</label>
                <textarea
                  required
                  rows={5}
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm font-mono"
                  placeholder="Enter document text..."
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowPasteModal(false)}
                  className="px-4 py-2 border rounded-lg text-slate-600 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-semibold"
                >
                  Index Document
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-base">Upload Document</h3>
              <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">{formError}</div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select File (TXT, MD, PDF)</label>
                <input
                  type="file"
                  required
                  accept=".txt,.md,.pdf"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadFile(e.target.files[0]);
                      if (!uploadTitle) setUploadTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
                    }
                  }}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Department</label>
                <select
                  value={uploadDept}
                  onChange={(e) => setUploadDept(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="HR">HR</option>
                  <option value="Finance">Finance</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Operations">Operations</option>
                  <option value="General">General</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Permitted Principals</label>
                <input
                  type="text"
                  value={uploadPrincipals}
                  onChange={(e) => setUploadPrincipals(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border rounded-lg text-slate-600 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-semibold"
                >
                  Upload & Index
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Document Modal */}
      {selectedDocId && docDetail && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <div>
                <h3 className="font-bold text-slate-900 text-base">{docDetail.title}</h3>
                <span className="text-xs text-slate-500 font-mono">ID: {docDetail.id}</span>
              </div>
              <button onClick={() => setSelectedDocId(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-100">
              <div>
                <span className="text-slate-500 block">Department:</span>
                <strong>{docDetail.department}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Chunks Count:</span>
                <strong>{docDetail.chunks_count || 1}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Status:</span>
                <strong>{docDetail.indexing_status}</strong>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase mb-1">Document Content</h4>
              <div className="p-3 bg-slate-900 text-slate-200 rounded-xl font-mono text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">
                {docDetail.raw_text}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedDocId(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit ACL Modal */}
      {aclDocId && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <h3 className="font-bold text-slate-900 text-base">Edit Document Permissions</h3>
              <button onClick={() => setAclDocId(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAclUpdate} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Permitted Principals (comma-separated)
                </label>
                <input
                  type="text"
                  required
                  value={aclInput}
                  onChange={(e) => setAclInput(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="e.g. general_employee, hr_analyst"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Removing a principal immediately revokes access, increments the document's ACL epoch, and purges that principal's cached answers.
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAclDocId(null)}
                  className="px-4 py-2 border rounded-lg text-slate-600 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-semibold"
                >
                  Save Permissions
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
