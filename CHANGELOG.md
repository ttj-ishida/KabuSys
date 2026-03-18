# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog 準拠の形式を採用しています。  
安定したリリースは [version] - YYYY-MM-DD の見出しで管理します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株の自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本情報とエクスポート対象を定義（__version__ = 0.1.0、__all__）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env、.env.local を自動的に読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS 環境変数は保護（protected）され、.env.local の override 動作でも意図しない上書きを防止。
  - .env パーサ:
    - export KEY=val 形式、クォート（シングル/ダブル）やバックスラッシュエスケープ、インラインコメントの扱いを考慮した安全なパース実装。
  - 必須設定取得ヘルパー (_require) と各種プロパティ:
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB/SQLite）などの設定をプロパティで提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティとデータ取得関数を実装:
    - 株価日足（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - 市場カレンダー（fetch_market_calendar）
  - 認証:
    - リフレッシュトークンから id_token を取得する get_id_token()（自動リフレッシュをサポート）。
    - モジュールレベルの id_token キャッシュを実装（ページネーション間で共有）。
  - 考慮された設計と挙動:
    - API レート制限尊重（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - リトライロジック（最大 3 回、指数バックオフ）と 408/429/5xx のハンドリング。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を利用して全件取得）。
    - データ取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するトレーサビリティを提供。
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE を用いて冪等に保存。
    - 型変換ユーティリティ (_to_float / _to_int) を実装し、空値や不正値を安全に扱う。
    - PK 欠損行はスキップし、スキップ数をログ出力。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し、前処理および DuckDB への保存を行う機能を実装。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いて XML Bomb 等の攻撃対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム／ホスト検証を行うカスタム HTTPRedirectHandler を導入。
      - ホスト名／IP をチェックしてプライベート/ループバック/リンクローカル/マルチキャスト宛てのアクセスを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、受信上限を超えるレスポンスや gzip 解凍後サイズ超過時は中断。
    - HTTP ヘッダ Content-Length の事前チェックと、実際の読み込みでの超過検査。
  - フィード処理:
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
    - 記事 ID は正規化 URL の SHA-256 を用い先頭32文字を採用して冪等性を確保。
    - テキスト前処理（URL除去、空白正規化）。
    - pubDate のパースと UTC での正規化（パース失敗時は現在時刻で代替しログ警告）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID を返す（チャンク＆単一トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けを一括挿入（ON CONFLICT で重複を無視）して挿入数を正確に返却。
  - 銘柄コード抽出:
    - 4桁数字を候補とする正規表現と、known_codes に基づくフィルタリング（重複除去）を実装。
  - 総合ジョブ:
    - run_news_collection: 複数 RSS ソースをループし、個別にエラーハンドリングして継続可能な収集を実装。新規記事に対して銘柄紐付けを一括処理。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema に基づき多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを作成:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（PRIMARY KEY、CHECK、FOREIGN KEY）を明記。
  - 頻出クエリ向けにインデックスを定義（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) を実装:
    - ファイルシステム上の親ディレクトリを自動作成。
    - 全 DDL とインデックスを用いて冪等的にテーブルを作成し、DuckDB 接続を返却。
  - get_connection(db_path) を実装（既存 DB へ接続、スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックに基づくユーティリティを実装。
  - ETLResult データクラス:
    - ETL 実行結果（取得数／保存数／品質問題／エラー一覧）を表現し、辞書化機能を提供。
    - 品質エラー検知（has_quality_errors）とエラー判定（has_errors）プロパティを提供。
  - テーブル存在確認・最終日付取得ユーティリティ:
    - _table_exists / _get_max_date / get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 市場カレンダー関連:
    - _adjust_to_trading_day: 非営業日の調整ロジック（最大 30 日遡る）を実装。
  - 差分更新（株価）ジョブ run_prices_etl の骨子を実装:
    - DB の最終取得日に基づく date_from 自動算出（backfill_days による再取得）。
    - J-Quants からの差分取得 → save_daily_quotes による保存フローを実装（関数内で取得数・保存数をログ出力）。
    - 初期データ開始日や calendar の先読み等の定数を定義（_MIN_DATA_DATE, _CALENDAR_LOOKAHEAD_DAYS, _DEFAULT_BACKFILL_DAYS）。

### 変更 (Changed)
- 初回リリースのため「変更」はありません（新規追加のみ）。

### 修正 (Fixed)
- 初回リリースのため「修正」はありません。

### セキュリティ (Security)
- RSS/HTTP 周りの複数のセキュリティ対策を導入:
  - defusedxml による XML パース保護。
  - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト時検証）。
  - レスポンスサイズ制限と gzip 解凍後のサイズチェック（DoS・圧縮爆弾対策）。
  - .env パースでクォートとエスケープを考慮し、予期しない環境変数読み込みを防止。

---

注:
- 本 CHANGELOG はコード内のドキュメント文字列や実装から推測して作成しています。動作や API の詳細は該当モジュールの docstring / 実装を参照してください。