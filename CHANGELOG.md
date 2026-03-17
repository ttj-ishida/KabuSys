# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針: 初期公開バージョンは 0.1.0 です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17

### Added
- 基本パッケージ初期実装を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
  - 自動ロード:
    - プロジェクトルートを .git または pyproject.toml を基準で検出し、プロジェクト配布後も動作する実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途）。
  - .env パーサー:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、コメント行と空行の無視。
    - 上書き（override）と保護（protected）オプションをサポートし、OS 環境変数を保護。
  - 必須変数取得時に未設定で ValueError を投げる _require ヘルパー。
  - 設定値の検証:
    - KABUSYS_ENV は development / paper_trading / live のみ有効。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効。
  - 主要プロパティ実装: J-Quants トークン、kabu API パスワード・ベースURL、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、環境判定ヘルパー（is_live 等）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装。
    - ページネーション対応で全件取得。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
  - 再試行/エラーハンドリング:
    - 指数バックオフによるリトライ（最大 3 回、408/429/5xx を対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - ネットワークエラー（URLError/OSError）もリトライ対象。
  - 認証:
    - refresh token から id_token を取得する get_id_token を実装。
    - 401 受信時は id_token を自動リフレッシュして一度だけリトライする安全なフロー（無限再帰防止フラグ）。
    - モジュールレベルの id_token キャッシュを保持し、ページネーション間で共有。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装（冪等性: ON CONFLICT DO UPDATE）。
    - 保存時に fetched_at を UTC タイムスタンプで記録し、いつデータを取得したかを追跡可能にする。
  - 型変換ユーティリティ:
    - _to_float / _to_int を提供。空値や変換失敗時の扱いを明示（int 変換では小数部の切り捨てを回避）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と DuckDB への保存ワークフローを実装。
  - セキュリティ/堅牢性:
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホスト/IP の事前検証を行うカスタムリダイレクトハンドラ。
      - ホスト名は DNS で A/AAAA を解決してプライベート/ループバック/リンクローカル/マルチキャストを検出。
    - 受信サイズ制限（最大 10 MB）と gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
    - HTTP ヘッダの Content-Length を考慮した事前チェック。
  - 記事処理/保存:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字で生成し冪等性を確保（utm_* 等を除去してからハッシュ化）。
    - テキスト前処理（URL 除去、空白正規化）。
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に新規保存された記事 ID を返す実装。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING RETURNING 1 を利用）し、挿入件数を正確に返す。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の4桁数字候補を抽出し、known_codes に含まれるものだけを返す（重複除去）。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースを巡回して収集・保存・銘柄紐付けを行う。各ソースは独立してエラーハンドリングし、1ソース失敗でも他ソースの処理は継続。

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - DataPlatform.md に基づく3+層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - Raw: raw_prices, raw_financials, raw_news, raw_executions
  - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature: features, ai_scores
  - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約・主キーを設定。
  - 頻出クエリ向けのインデックスを定義（例: prices_daily(code, date) 等）。
  - init_schema(db_path) でディレクトリ作成・DDL 実行を行い、冪等にスキーマ初期化を行う。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass を追加し、実行結果の構造化（取得数・保存数・品質問題・エラー等）を定義。
  - 差分取得ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - 市場カレンダーに基づく取引日補正関数 _adjust_to_trading_day を実装（最大30日遡る）。
  - run_prices_etl:
    - 差分更新ロジック（DB の最終取得日から backfill_days を使って再取得する実装方針）。
    - デフォルトの backfill_days は 3、初回ロードの最小日付は 2017-01-01。
    - J-Quants クライアントの fetch/save を利用して取得と保存を行う。
    - id_token を引数で注入可能にしてテスト容易性を確保。

### Security
- XML パースに defusedxml を利用し、XML 関連攻撃（XML Bomb 等）に対処。
- RSS フェッチでの SSRF 対策実装（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
- .env パーサーはパスワード等の取り扱いで OS 環境変数保護機能を提供。

### Notes / Migration
- .env の自動読み込みはプロジェクトルート検出に依存します。配布環境で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の init_schema() は指定パスの親ディレクトリを自動作成します。インメモリ DB は ":memory:" を使用してください。
- J-Quants API のレート制御とリトライはライブラリ側で行いますが、運用時は API 利用制限にも注意してください。

### Known / Implementation remarks
- ETL パイプラインは差分取得・バックフィルの方針を実装していますが、今後の拡張（品質チェックモジュール quality の実装詳細・処理継続ポリシー等）が想定されます。
- run_news_collection / run_prices_etl 等はログ出力を伴い、部分的なエラー発生時も他ソースや他データの処理を継続する設計です。

## Deprecated
- なし

## Removed
- なし

## Fixed
- なし（初期リリース）

（以上）