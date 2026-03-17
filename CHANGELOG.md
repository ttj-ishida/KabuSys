CHANGELOG
=========

すべてのリリースは「Keep a Changelog」準拠の形式で記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 開発中の改善・単体テスト用フラグが存在します（例: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 一部モジュールでは今後追加予定の品質チェックやエラーハンドリング拡張の余地あり（data.pipeline や quality モジュール連携周り）。

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動的に読み込む機能を実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサは export プレフィックス、シングル／ダブルクォート、バックスラッシュによるエスケープ、行内コメントの取り扱いに対応。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パスなど主要設定プロパティを取得（必須設定は未設定時に ValueError を送出）。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - LOG_LEVEL 検証（DEBUG/INFO/...）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）:
    - レート制限 (120 req/min) を守る固定間隔スロットリングを組み込み（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大リトライ回数、408/429/5xx をリトライ対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は自動で ID トークンをリフレッシュして 1 回だけリトライ（無限ループ防止の仕組みあり）。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
  - 認証補助: get_id_token(refresh_token) を実装。
  - データ取得 API:
    - fetch_daily_quotes: 株価（OHLCV）をページネーションで取得。
    - fetch_financial_statements: 四半期 BS/PL をページネーションで取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得。
  - DuckDB への保存関数（冪等性を意識）:
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE。
  - データ整形ユーティリティ: _to_float / _to_int（不正値への耐性実装）。
  - fetched_at に UTC タイムスタンプを格納して Look-ahead バイアスのトレースを可能に。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得・前処理・保存のワークフロー実装:
    - fetch_rss: RSS 取得、defusedxml による安全な XML パース、gzip 解凍対応、Content-Length/サイズ上限チェック（10 MB）、レスポンス超過の検出。
    - preprocess_text: URL 除去・空白正規化。
    - _normalize_url / _make_article_id: トラッキングパラメータを除去して URL 正規化、正規化 URL から SHA-256（先頭32文字）で記事IDを生成し冪等性を保証。
    - SSRF 対策: リダイレクト時のスキーム検証とホストのプライベートアドレス判定、ホストの事前検証。
    - save_raw_news: DuckDB の raw_news テーブルへチャンク単位で INSERT ... RETURNING を用いて新規挿入 ID を返す（トランザクションまとめて実行し失敗時はロールバック）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING + RETURNING で正確な挿入数を算出）。
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し既知銘柄セットでフィルタ（重複除去）。
    - run_news_collection: 複数ソースから並列（逐次だが各ソース個別にエラー吸収）に収集し DB に保存、銘柄紐付けを一括処理。
  - セキュリティ設計:
    - defusedxml による XML 攻撃対策。
    - SSRF / プライベートネットワークへのアクセス防止。
    - レスポンスサイズ制限と Gzip 解凍後の検査で Zip/Gzip ボム対策。
    - URL スキーム検査で file:, javascript:, mailto: 等を排除。
  - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）を定義。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに型・CHECK 制約・主キー・外部キーを細かく付与。
  - 頻出クエリ向けのインデックス定義を追加（code/date や status など）。
  - init_schema(db_path): ディレクトリ自動作成や DDL を順序付けて実行し冪等にスキーマ初期化を行う関数を提供。
  - get_connection(db_path): 既存 DB への接続を返すユーティリティ。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass を実装（ETL のメタ情報・品質問題・エラーを格納、シリアライズ可能）。
  - 差分更新のためのヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: 各 raw テーブルの最終取得日を取得。
    - _adjust_to_trading_day: 非営業日を直近の営業日に調整（market_calendar の存在を前提としたロジック）。
    - 差分更新ポリシー: デフォルトで backfill_days=3 を用いて最終取得日からの再取得で API 後出し修正を吸収。
  - run_prices_etl を実装（差分計算→fetch_daily_quotes→save_daily_quotes のフロー）。品質チェックモジュール（quality）との連携ポイントを用意。

- パッケージ初期構成ファイル
  - src/kabusys/__init__.py にバージョンと公開サブパッケージリストを定義。
  - strategy/execution/monitoring のパッケージ雛形を用意（将来的な機能追加用）。

Security
- RSS 処理における SSRF 対策、defusedxml による XML 攻撃対策、レスポンス長の上限、gzip 解凍後のサイズチェックなど多層的な安全策を導入。
- .env 読み込み時の上書き保護（OS 環境変数保護）機能を提供。

Changed
- 初公開のため過去のリリースとの互換性変更はなし。

Fixed
- 初版リリースのため過去のバグ修正履歴なし。

Removed
- 該当なし。

Notes / Known limitations
- data.pipeline 内で quality モジュールに依存する箇所があり、quality モジュールの実装・ポリシーにより挙動が変わります（品質チェックは ETL を中断せず問題を報告する設計）。
- strategy/execution/monitoring は雛形が存在する状態で、実際の自動売買ロジックや発注実装は今後追加予定です。
- run_prices_etl 等の一部処理フローは今後の拡張（ログ詳細化、メトリクス計測、より細かな失敗リトライ戦略）で改善予定。

Authors
- 初期実装: 開発者チーム（コードベースより推測して記載）

License
- ソースコード内に明示的なライセンス記述が見当たりません。配布時は適切なライセンスを付与してください。