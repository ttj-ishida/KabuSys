# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠の形式を採用しています。  

※日付はパッケージの __version__ に基づく初回リリース日として 2026-03-17 を使用しています。

## [Unreleased]
- なし（今後の変更記録用）

## [0.1.0] - 2026-03-17
初期リリース。日本株の自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期エントリポイント（src/kabusys/__init__.py）。サブパッケージを公開: data, strategy, execution, monitoring。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 設定管理
  - 環境変数読み込みと管理モジュール（src/kabusys/config.py）。
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
    - export KEY=val 形式やクォート・インラインコメントに対応した .env パーサ実装。
    - 設定取得用 Settings クラス（J-Quants / kabu ステーション / Slack / DB パス / 環境種別・ログレベル判定プロパティ等）。
    - 必須環境変数未設定時に ValueError を送出する _require 関数。

- データ取得（J-Quants）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）。
    - API ベース実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
    - 固定間隔スロットリングによるレート制限（120 req/min）実装。
    - リトライ（指数バックオフ、最大 3 回）・HTTP 429 の Retry-After 対応。
    - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key の連結取得）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT DO UPDATE）。
    - 値変換ユーティリティ（_to_float, _to_int）を実装（不正値は None に正しく扱う）。

- ニュース収集
  - RSS 収集・保存モジュール（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（デフォルトソースに Yahoo Finance を設定）。
    - defusedxml を用いた安全な XML パース。
    - SSRF 対策（URL スキーム検証、リダイレクト先のスキーム・プライベートIP検査、カスタムリダイレクトハンドラ）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と SHA-256 ベースの安定した記事 ID 生成。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB への一括挿入（チャンク化、トランザクション、INSERT ... RETURNING を利用して実際に挿入された ID を返す）。
    - 銘柄コード抽出ロジック（4桁コードの正規表現と known_codes フィルタリング）。
    - run_news_collection による複数ソース一括収集 + 銘柄紐付け処理。

- スキーマ管理
  - DuckDB 用スキーマ定義と初期化モジュール（src/kabusys/data/schema.py）。
    - Raw / Processed / Feature / Execution の多層テーブル定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions など）。
    - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）と推奨インデックス定義を含む DDL。
    - init_schema(db_path) によるディレクトリ自動作成＋全テーブル／インデックス作成（冪等）。
    - get_connection(db_path) の提供。

- ETL パイプライン
  - ETL ヘルパーと run_prices_etl 等の下地（src/kabusys/data/pipeline.py）。
    - ETLResult データクラス（取得件数、保存件数、品質チェック結果、エラー集約など）。
    - テーブル存在チェック・最終日取得ユーティリティ。
    - 市場カレンダーに基づく営業日調整ヘルパー。
    - 差分更新ロジック（最終取得日からの backfill デフォルト 3 日）を用いた run_prices_etl の基礎実装（API 取得→保存の流れ）。
    - 品質チェック（quality モジュール連携を想定）を継続的に実行し、致命的品質問題があっても ETL を継続する設計方針。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- ニュース収集での複数のセキュリティ対策を実装：
  - defusedxml による XML パース（XML Bomb 等の防御）。
  - URL スキーム検証（http/https のみ許可）とプライベートネットワーク/IP のブロック（SSRF対策）。
  - レスポンスサイズ制限と Gzip 解凍後のサイズチェックによるメモリ DoS 対策。

### Notes / Implementation details
- ネットワーク/外部依存の処理はログ出力と例外伝播を適切に行う設計で、個々のソース失敗が全体を停止させないよう例外ハンドリングされています。
- テスト容易性のため、一部のネットワーク呼び出し（例: news_collector._urlopen）はモック差替え可能に実装されています。
- DuckDB への書き込みは基本的にトランザクションでまとめて行い、冪等性（ON CONFLICT）を担保しています。

### Breaking Changes
- なし（初回リリース）

### Deprecations
- なし

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの具体的な戦略実装や注文実行フロー（kabu ステーション連携）、監視・アラート機能の追加、quality モジュールによる具体的な品質チェック実装などを予定しています。