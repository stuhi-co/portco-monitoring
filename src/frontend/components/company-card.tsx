"use client";

import { Trash2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CompanyResponse } from "@/lib/api";

interface CompanyCardProps {
  company: CompanyResponse;
  onRemove: (id: string) => void;
  removing: boolean;
}

export function CompanyCard({ company, onRemove, removing }: CompanyCardProps) {
  const isEnriching = company.enriched_at === null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base">{company.name}</CardTitle>
          <div className="flex items-center gap-2">
            {company.industry && (
              <Badge variant="secondary" className="text-xs">
                {company.industry.replace(/_/g, " ")}
              </Badge>
            )}
            {isEnriching ? (
              <Badge variant="outline" className="text-xs">
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                Enriching...
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="border-primary/30 bg-primary/10 text-xs text-primary"
              >
                Enriched
              </Badge>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
          onClick={() => onRemove(company.id)}
          disabled={removing}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardHeader>
      {!isEnriching && (
        <CardContent className="space-y-3 text-sm">
          {company.description && (
            <p className="text-muted-foreground">{company.description}</p>
          )}
          {company.competitors && company.competitors.length > 0 && (
            <div>
              <span className="font-medium">Competitors: </span>
              <span className="text-muted-foreground">
                {company.competitors.join(", ")}
              </span>
            </div>
          )}
          {company.key_topics && company.key_topics.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {company.key_topics.map((topic) => (
                <Badge key={topic} variant="secondary" className="text-xs">
                  {topic}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
