# Changelog

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠します。  

※初期リリース (v0.1.0)：コードベースから推測できる主要機能・設計方針をまとめています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期構成
  - kabusys パッケージの公開APIとして data / strategy / execution / monitoring をエクスポート。
  - バージョン情報: `__version__ = "0.1.0"`。

- 環境設定/ローダー（kabusys.config）
  - .env/.env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env 行パーサ（クォート、エスケープ、export プレフィックス、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants/Kabu API/Slack/DBパス/ログレベル/環境種別等の取得・検証を実装。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL の妥当性チェック。
    - Path 型での DB パス取得（duckdb/sqlite）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar 等の取得）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 408/429/5xx を対象にリトライ。
  - 401 受信時は ID トークン自動リフレッシュして1回リトライ（再帰防止の allow_refresh 制御）。
  - ページネーション対応（pagination_key を用いたループ）。
  - DuckDB へ冪等に保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）：
    - fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による重複排除。
  - 入出力変換ユーティリティ (`_to_float`, `_to_int`)。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードのフェッチと記事パース機能（fetch_rss）。
  - defusedxml を用いた安全な XML パース。gzip 圧縮対応、Content-Length と実読み込みサイズの上限チェック（MAX_RESPONSE_BYTES = 10MB）。
  - SSRF 対策:
    - リダイレクト時にスキーム/ホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - 初回URLと最終URLのホストがプライベートアドレスかチェック（_is_private_host）。
    - http/https 以外のスキームを拒否。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出（4桁数値パターン + known_codes フィルタ）。
  - DB 保存ユーティリティ（save_raw_news / save_news_symbols / _save_news_symbols_bulk）：
    - チャンク分割、トランザクション管理、INSERT ... RETURNING による実際に挿入されたレコード検出、ON CONFLICT DO NOTHING による冪等性。
  - デフォルト RSS ソース定義（例: yahoo_finance）。

- リサーチ・ファクター（kabusys.research）
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）：prices_daily を参照して複数ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）：ファクターと将来リターンの Spearman ランク相関を算出。必要最小レコード数チェック、NaN/無限値除外。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸めで ties 検出漏れを防止。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を算出（None を除外）。
  - factor_research モジュール:
    - Momentum（calc_momentum）：mom_1m/mom_3m/mom_6m と MA200 乖離を計算（ウィンドウ不足時は None）。
    - Volatility（calc_volatility）：ATR20、相対ATR(atr_pct)、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播に注意した実装。
    - Value（calc_value）：raw_financials の直近財務データと prices_daily を組み合わせて PER/ROE を算出。
  - いずれの関数も DuckDB 接続を受け取り、prices_daily / raw_financials だけを参照（外部APIへのアクセスなし、冪等/安全設計）。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL 定義（Raw Layer のテーブル定義を含む）:
    - raw_prices, raw_financials, raw_news, raw_executions などの CREATE TABLE 文（主キー・制約付き）。
  - 初期化・設計方針コメント（Raw / Processed / Feature / Execution 層の説明）。

- その他
  - ロギング出力を適切に行うよう logger 呼び出しを多数追加（処理件数、警告、例外など）。
  - モジュール間での明示的な依存分離（リサーチは DB のみ参照、発注APIや本番口座へのアクセスをしない旨をドキュメントコメントで明記）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサで defusedxml を使用し XMLBomb 等への対策を実装。
- RSS フェッチ処理で SSRF 対策を多層で実施（事前ホスト検査・リダイレクト検査・スキーム検証）。
- ネットワーク応答のサイズ上限と gzip 解凍後のサイズ検査でメモリ DoS を軽減。
- J-Quants クライアントでトークンの自動更新を制御し無限再帰を防止。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後やパッケージ化後に挙動を変更したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB スキーマは CREATE TABLE を含むため、既存 DB への適用はスキーマ設計に合わせてマイグレーションが必要です（特に制約や PRIMARY KEY に注意）。
- news_collector の既知銘柄一覧（known_codes）は外部で用意して渡す設計になっています。未提供時は銘柄抽出/紐付け処理がスキップされます。

---

もし必要であれば、各モジュールの利用例や API の簡単な使用方法（コードスニペット）を別ファイルにまとめて提供できます。どの情報を優先して記載しますか？