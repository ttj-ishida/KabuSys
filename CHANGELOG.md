# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし（初期リリース以降の未リリース変更はここに記載します）

## [0.1.0] - 2026-03-15

### 追加
- 初期リリースを公開。
  - パッケージ名: `kabusys`
  - バージョン情報を `src/kabusys/__init__.py` に定義:
    - `__version__ = "0.1.0"`
    - パッケージ説明の docstring: "KabuSys - 日本株自動売買システム"
    - `__all__ = ["data", "strategy", "execution", "monitoring"]` により主要サブパッケージを公開
  - サブパッケージのスケルトンを追加（現時点では初期化ファイルのみ）:
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - 目的（設計上の領域）:
    - data: 市場データの取得・管理
    - strategy: 売買戦略の実装
    - execution: 注文送信や約定処理
    - monitoring: 状態監視・ログ・アラート

### 変更
- なし

### 修正
- なし

### 非推奨（Deprecated）
- なし

### 削除
- なし

### セキュリティ
- なし

---

将来的な変更予定（例）
- 各サブパッケージに実装を追加（データ取得クライアント、戦略テンプレート、注文実行ラッパー、監視ダッシュボード等）
- テスト・ドキュメントの整備
- CI/CD とパッケージ化（PyPI公開等）

（この CHANGELOG はコードベースから推測して作成しています。実際の履歴やコミットログがある場合はそれに基づいて更新してください。）