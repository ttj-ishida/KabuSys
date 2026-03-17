CHANGELOG
=========

すべての重要な変更はここに記録します。  
このファイルは Keep a Changelog の形式に従って作成されています。

[unreleased]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-03-17
------------------

Added
- 基本パッケージ構成を導入
  - パッケージ名: kabusys、バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public API: data, strategy, execution, monitoring をエクスポートする準備。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定は .git / pyproject.toml を基準に行い、パッケージ配布後も CWD に依存しない検出を実現。
  - .env パーサは以下に対応:
    - 空行・コメント行の無視
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - クォートなし値でのインラインコメント判定（直前が空白/タブの場合）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを提供し、J-Quants トークン・kabu API 設定・Slack トークン・DB パス・環境名（development/paper_trading/live）・ログレベルの取得とバリデーションを実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しの共通ロジックを提供: _request().
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する _RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダ優先。
  - 401 ハンドリング: ID トークン自動リフレッシュを 1 回行い再試行（無限再帰防止）。
  - ID トークン取得: get_id_token()（POST /token/auth_refresh）。
  - データ取得関数:
    - fetch_daily_quotes(): 日次株価（ページネーション対応）
    - fetch_financial_statements(): 四半期財務（ページネーション対応）
    - fetch_market_calendar(): JPX マーケットカレンダー
  - DuckDB への保存（冪等）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar() は ON CONFLICT ... DO UPDATE を利用して重複を排除・更新。
  - 取得時刻 (fetched_at) を UTC で記録し、Look-ahead Bias のトレースが可能。
  - 型変換ユーティリティ: _to_float(), _to_int()（不正値は None）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news テーブルへの保存ワークフローを実装:
    - fetch_rss(): RSS 取得、XML パース（defusedxml 利用）、前処理、記事リスト生成
    - save_raw_news(): INSERT ... RETURNING を用いて新規挿入記事IDのリストを返す（チャンク処理、トランザクション）
    - save_news_symbols(), _save_news_symbols_bulk(): 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING）
    - run_news_collection(): 複数 RSS ソースの統合収集ジョブ
  - セキュリティ対策 / 頑健化:
    - defusedxml を使用して XML Bomb 等を防止
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト時のスキーム・プライベートアドレス検証（_SSRFBlockRedirectHandler）、ホストのプライベートアドレス検出（_is_private_host）
    - レスポンスサイズ上限を設定（MAX_RESPONSE_BYTES = 10MB）し、gzip 解凍後もサイズ検査
    - URL 正規化: トラッキングパラメータ（utm_* 等）除去、スキーム/ホスト小文字化、フラグメント削除（_normalize_url）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
    - テキスト前処理: URL 除去・空白正規化（preprocess_text）
    - 銘柄抽出: 4桁コード検出と known_codes によるフィルタ（extract_stock_codes）
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ RSS）

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づき、Raw / Processed / Feature / Execution レイヤーのテーブル定義を実装。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与し、頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) により親ディレクトリの自動作成、冪等的なテーブル作成を行い DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass を導入し、ETL 実行結果、品質問題、エラー集計を保持。
  - テーブル存在チェック・最大日付取得ユーティリティ (_table_exists, _get_max_date) を実装。
  - market_calendar を用いた非営業日調整ヘルパー (_adjust_to_trading_day) を実装。
  - 差分更新を支援する関数:
    - get_last_price_date(), get_last_financial_date(), get_last_calendar_date()
  - run_prices_etl(): 株価差分 ETL（差分開始日の自動算出、backfill_days による後出し修正吸収、jquants_client の fetch/save を利用）

Changed
- 初版リリースのための公開 API と内部ユーティリティを整備。プロジェクトの土台作成に注力。

Security
- defusedxml を使用した XML パースで XML 関連攻撃対策を導入（news_collector）。
- RSS フェッチで SSRF 対策（リダイレクト前検査・ホストのプライベート IP 判定・スキーム制限）。
- 外部入力（.env）パースを厳密に行い、意図しない解釈を防止。

Known issues / Notes
- run_prices_etl の末尾が実装途中の痕跡（ファイル末尾が切れているように見える）で、現状の戻り値が不完全な状態です。ETL の追加ジョブや戻り値の最終調整が必要です。
- src/kabusys/execution/__init__.py / src/kabusys/strategy/__init__.py はプレースホルダとして空ファイルが存在します。実装は今後追加予定です。
- テストコードは同梱されていません（ユニットテスト・統合テストは別途整備推奨）。
- ネットワーク関連呼び出し（RSS / J-Quants）では urllib を直接使用しており、より高機能な HTTP クライアント（例: requests, httpx）に差し替える余地があります。
- DuckDB への SQL 実行はプレースホルダを使用していますが、SQL インジェクションに注意が必要な動的 SQL 部分がないか今後レビュー推奨。

Compatibility
- Python 3.10+ を想定（型アノテーション、Path型の使用、| ユニオン記法など）。
- DuckDB と defusedxml に依存。

Authors
- 初期実装: 開発チーム

---

注: 今後のリリースでは run_news_collection のエラー集計、ETL の追加ジョブ（financials, calendar の差分 ETL、品質チェックモジュール integration）、strategy/execution モジュールの実装、ユニットテスト追加などを計画してください。