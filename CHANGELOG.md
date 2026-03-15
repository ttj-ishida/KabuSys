# CHANGELOG

すべての重要な変更を記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従い、セマンティックバージョニング（SemVer）を採用します。

まとめ:
- プロジェクト名: KabuSys（日本株自動売買システム）
- 初期リリース（スケルトン）：0.1.0

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
初期リリース。プロジェクトの骨組み（パッケージ構成）を追加しました。

### 追加 (Added)
- ベースパッケージを追加
  - `src/kabusys/__init__.py`
    - パッケージドキュメンテーション文字列: "KabuSys - 日本株自動売買システム"
    - バージョン識別子 `__version__ = "0.1.0"` を設定
    - 外部公開シンボルとして `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義
- サブパッケージ（スケルトン）を追加
  - `src/kabusys/data/__init__.py` — データ取得・管理用サブパッケージ（現時点ではプレースホルダ）
  - `src/kabusys/strategy/__init__.py` — 売買戦略実装用サブパッケージ（プレースホルダ）
  - `src/kabusys/execution/__init__.py` — 注文実行／ブローカー連携用サブパッケージ（プレースホルダ）
  - `src/kabusys/monitoring/__init__.py` — 監視・ログ・メトリクス用サブパッケージ（プレースホルダ）

### 変更 (Changed)
- なし（初回リリースのため）

### 修正 (Fixed)
- なし

### 削除 (Removed)
- なし

Notes / 今後の予定:
- 各サブパッケージは現段階で __init__.py が空のスケルトンになっているため、データ取得、戦略ロジック、注文の送信、監視機能等の具体実装を追加する必要があります。
- 次のマイナー/パッチリリースでは、各サブパッケージに具体的なモジュール（例: data.fetcher, strategy.simple, execution.adapter, monitoring.metrics など）を追加する予定です。
- CHANGELOG はリリースごとに更新してください。