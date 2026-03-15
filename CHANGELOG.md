# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
### Added
- 初回リリース (パッケージ名: `kabusys`)。
  - パッケージのメタ情報を定義:
    - `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。
    - `__all__ = ["data", "strategy", "execution", "monitoring"]` を公開。
  - サブパッケージのスケルトン（空の初期化ファイル）を追加:
    - `src/kabusys/data/__init__.py` (データ取り込み / 市場データ関連の責務を想定)
    - `src/kabusys/strategy/__init__.py` (売買ロジック / シグナル生成を想定)
    - `src/kabusys/execution/__init__.py` (注文発行 / ブローカー連携を想定)
    - `src/kabusys/monitoring/__init__.py` (監視・ログ・状態管理を想定)
- プロジェクトの目的（推定）:
  - 日本株向けの自動売買システムの骨組みを提供するための初期構成を作成。

### Notes
- 現時点では各サブパッケージはプレースホルダ（空の `__init__.py`）であり、具体的な実装は未着手です。
- 今後の予定（想定）:
  - `data`：マーケットデータの取得・正規化・保存機能の実装
  - `strategy`：ストラテジー定義とバックテスト機能の実装
  - `execution`：証券会社APIとの注文発行・約定管理の実装
  - `monitoring`：稼働監視・ログ・アラート機能の実装

---