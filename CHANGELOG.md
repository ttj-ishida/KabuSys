# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更はバージョン単位で記載
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

## [Unreleased]
（次回リリースに向けた変更点や予定をここに記載）

---

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを "0.1.0" として公開。
  - 公開サブパッケージ: data, strategy, execution, monitoring（strategy と execution は初期空ディレクトリとして準備）。

- 環境設定管理（kabusys.config）
  - .env ファイル（`.env` / `.env.local`）および OS 環境変数から設定を読み込む自動ローダーを追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して判定（配布後も動作するよう設計）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env パーサーの実装:
    - `export KEY=val` 形式へ対応。
    - クォート（シングル/ダブル）内のバックスラッシュエスケープ処理。
    - コメント処理（クォートなしで '#' の前が空白/タブのときのみコメント扱い）。
  - Settings クラスを実装して型安全に設定値を提供:
    - J-Quants、kabuステーション、Slack、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）、ログレベル等の設定取得プロパティを提供。
    - 必須値が未設定の場合は明確な ValueError を発生させる。
    - env/log_level の値検証を実装（不正値は例外）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装:
    - ベース URL、レート制限（120 req/min）、最小インターバル制御（固定間隔スロットリング）を組み込み。
    - 自動リトライ（指数バックオフ、最大 3 回）およびリトライ対象ステータス管理（408, 429, 5xx）。
    - 401 レスポンス時はリフレッシュトークンを使って id_token を自動更新し 1 回再試行（無限再帰防止）。
    - レスポンス JSON のデコード失敗時に詳細メッセージを返す。
    - モジュールレベルの id_token キャッシュ（ページネーションをまたいで共有）を実装。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー: 祝日・半日・SQ）
    - 取得件数のログ出力を実施。
  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存。
    - PK 欠損行のスキップとログ出力。
    - 各列の変換ユーティリティ (_to_float / _to_int) を実装し、不正値を安全に None に変換。
  - テスト容易性: id_token を注入可能。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得して DuckDB の raw_news へ保存する機能を実装。
  - セキュリティ / ロバストネス設計:
    - defusedxml を用いた XML パース（XML Bomb 等の防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前スキーム/プライベートIP検証（カスタム HTTPRedirectHandler）、ホストのプライベートアドレス判定（DNS 解決結果 / 直接 IP 判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent、Accept-Encoding の指定。
    - fetch_rss は XML パースエラーやセキュリティ違反時に安全に空リストを返す設計。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid など）を除去して URL を正規化。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を使用して冪等性を確保。
  - テキスト前処理:
    - URL 削除、空白正規化などの preprocess_text を提供。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事IDのみを返す（チャンク分割、1 トランザクションで処理）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存し、実際に挿入された件数を返す。
    - トランザクション管理（begin/commit/rollback）と例外時のログ出力を実装。
  - 銘柄コード抽出:
    - 4桁数値パターン（例 "7203"）から候補を抽出し、 known_codes に登録されたもののみを返す関数を実装。
  - 統合収集ジョブ:
    - run_news_collection: 複数 RSS ソースの順次処理、ソース単位でエラーハンドリング（1 ソース失敗でも他は継続）、新規件数・紐付け保存を行う。

- DuckDB スキーマ定義 & 初期化（kabusys.data.schema）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに対するチェック制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) を実装:
    - 指定パスの親ディレクトリ自動作成（file DB の場合）。
    - 全 DDL とインデックスを冪等に実行して初期化済みの DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約、辞書化可能。
  - 品質チェックとの連携を想定（quality モジュールの QualityIssue を扱うためのフィールドを用意）。
  - DuckDB 上の最終取得日確認ユーティリティ:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date（テーブル未作成または空の場合は None を返す）。
  - 市場カレンダー補助:
    - _adjust_to_trading_day: 非営業日の場合に直近の営業日に調整するロジック。
  - 差分更新ロジック:
    - run_prices_etl:
      - date_from 未指定時は DB の最終取得日から backfill_days 日分差し戻して再取得（デフォルト backfill_days=3、API の後出し修正に対応）。
      - 最小取得日を _MIN_DATA_DATE（2017-01-01）として扱う。
      - jq.fetch_daily_quotes → jq.save_daily_quotes を用いて取得と保存を行い、取得件数と保存件数を返す。
  - 設計指針:
    - デフォルトでは営業日単位で差分更新を行う。
    - id_token を引数で注入可能にしてテストしやすくしている。
    - 品質チェックは Fail-Fast ではなく、問題を収集して呼び出し元に通知する方針。

### Security
- RSS 取得部分に対して複数の SSRF 対策を実装（スキーム検査、プライベートアドレス検出、リダイレクト時検査）。
- defusedxml を使用して XML パースの安全性を強化。
- レスポンスサイズ制限・gzip 解凍後検査で DoS 補強。

### Notes / その他
- ネットワーク / I/O 周りは明示的にログ出力しており、障害時の調査がしやすい設計。
- 一部関数（例: _urlopen）はテスト時にモック差し替えが容易になるよう設計。
- strategy / execution / monitoring はパッケージ構造のみ用意しており、今後の拡張を想定。

---

今後の予定（例）
- ETL の品質チェック（quality モジュール）を実装して pipeline と接続
- 戦略（strategy）と発注（execution）ロジック実装（paper/live の挙動制御）
- モニタリング / 通知（Slack 連携）実装
- 単体テスト・統合テストの充実化（外部 API をスタブ化して CI に組み込む）

もし特定ファイルごと、またはより詳細な変更点（関数単位の説明や設計意図）を個別に記載したい場合は、対象を指定してください。