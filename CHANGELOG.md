# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
タグ付けは semantic versioning に基づきます。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初期リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py を追加。バージョン情報と公開モジュール（data, strategy, execution, monitoring）を定義。
- 設定管理（src/kabusys/config.py）
  - .env および環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS環境 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パーサー（クォート対応、export プレフィックス対応、インラインコメント処理）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証などを提供。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーを取得する fetch_* API を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）を実装。
  - 401 応答時にリフレッシュトークンで自動再取得して1回リトライする仕組みを実装。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - DuckDB へ保存する save_* 関数を実装（fetched_at を UTC で記録、ON CONFLICT DO UPDATE による冪等性）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し、raw_news テーブルへ冪等保存する処理を実装（記事IDは正規化URLのSHA-256先頭32文字）。
  - defusedxml を用いた安全な XML パース、gzip 圧縮対応、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）による DoS対策を実装。
  - SSRF 対策：URL スキーム検証、プライベート/ループバックアドレス判定、リダイレクト時の事前検証ハンドラを実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - テキスト前処理（URL除去・空白正規化）および銘柄コード抽出（4桁数字フィルタ・既知コードチェック）を実装。
  - DuckDB へのバルク挿入をチャンク化してトランザクションで処理。INSERT ... RETURNING を利用して実際に挿入された件数/IDを取得。
  - run_news_collection により複数ソースの独立した収集処理と銘柄紐付け（news_symbols）をサポート。
- スキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 用の完全なスキーマ定義を実装（Raw / Processed / Feature / Execution レイヤーに対応）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー、features, ai_scores などの Feature レイヤー、signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution レイヤーを定義。
  - 適切な CHECK 制約、PRIMARY/FOREIGN KEY、インデックス定義、テーブル作成順を用意し、init_schema(db_path) で初期化可能。
  - get_connection(db_path) で既存 DB への接続を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の枠組みを実装（最終取得日からの差分取得、backfill_days による後出し修正吸収）。
  - 市場カレンダーの先読みや品質チェックフック（quality モジュール参照）を考慮した設計。
  - ETLResult データクラスで処理結果・品質問題・エラーの集約および to_dict による可視化を実装。
  - raw_prices/raw_financials/market_calendar の最終取得日の取得ユーティリティおよび run_prices_etl の差分ETLロジック（fetch → save）を実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- RSS パーサーに defusedxml を利用して XML Bomb 等の攻撃を軽減。
- HTTP クライアント側で SSRF 対策を多数導入（スキーム検証、プライベートIP判定、リダイレクト検査、受信サイズ制限、gzip 解凍後のサイズチェック）。
- .env 読み込み時に OS 環境変数の上書きを防ぐ protected 機構を導入。

### Notes / Migration
- .env 自動読み込みはデフォルトで有効です。CI/テスト環境等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を使用してください。既存スキーマがある場合は冪等にスキップされます。
- J-Quants の認証トークンは Settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）に依存します。未設定の場合は ValueError が発生します。
- news_collector の extract_stock_codes は known_codes セットと組み合わせて使用する想定です。既知銘柄リストを渡さない場合は紐付け処理をスキップできます。

---

この CHANGELOG はコードベースの現状（初期リリース）から推測して作成しています。将来のリリースでは各カテゴリに沿って変更点を追記してください。