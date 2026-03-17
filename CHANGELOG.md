# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリのコードベースから推測して作成した変更履歴（初期リリース）です。

全般的な表記:
- 日付はリリース日を示します。
- 各項目では導入された主要な機能、設計上の注記、セキュリティ対策などを簡潔に記載しています。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-17

Initial release — 日本株自動売買のための基盤ライブラリを初期実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ で列挙。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml で探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env 行パーサー: export プレフィックス、クォート、エスケープ、インラインコメントの扱いを考慮。
  - Settings クラスを提供し、J-Quants トークン、kabuステーションパスワード、Slack トークン/チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベルの検証を行うプロパティを実装。
  - 必須環境変数未設定時の明示的エラー (_require)。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントの初期実装:
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - 認証トークン取得/更新機能（get_id_token）とモジュールレベルの ID トークンキャッシュ。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライポリシー:
    - 指数バックオフ、最大 3 回のリトライ（対象: 408, 429, >=500、429 は Retry-After ヘッダを優先）。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止処理あり）。
  - DuckDB へ保存する冪等関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - ON CONFLICT DO UPDATE による重複排除／更新。
    - fetched_at を UTC で記録して取得時刻をトレース可能に（Look-ahead Bias 対策）。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値や空値に対する扱いを明確化。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集・前処理・DB 保存の一連処理を実装（DataPlatform.md に準拠した設計）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - fetch_rss 前にホストがプライベートアドレスか検証。
      - リダイレクト時にスキームとホスト検証を行う _SSRFBlockRedirectHandler を導入。
      - URL スキームは http/https のみ許可。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 受信ヘッダ Content-Length の事前チェック。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_* 等）の除去、クエリソート、フラグメント削除などを行う _normalize_url。
    - 正規化 URL から SHA-256 の先頭32文字を記事 ID として生成（_make_article_id）。
  - テキスト前処理（URL 除去・空白正規化）と pubDate のパース（_parse_rss_datetime）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を用い、新規挿入された記事IDを正確に返す。チャンク処理とトランザクションで効率化。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複排除）し、INSERT ... RETURNING で実挿入数を返す。
  - 銘柄コード抽出（extract_stock_codes）:
    - 4桁数字を候補に抽出し、known_codes にあるもののみ返す（重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層をカバーするテーブル DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を付与。
  - 検索を想定したインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) によりディレクトリ作成→全DDL とインデックスを実行して初期化するユーティリティを提供。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計方針と差分更新ロジックを文書化。
    - 最小データ日（_MIN_DATA_DATE）、カレンダー先読み、デフォルトバックフィル日数などの定数を導入。
  - ETLResult dataclass を実装し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を構造化して返せるようにした。
  - DB ヘルパー:
    - テーブル存在チェック (_table_exists)、最大日付取得ユーティリティ (_get_max_date)。
    - 市場カレンダーに基づいた営業日調整 (_adjust_to_trading_day)。
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数。
  - 個別ジョブの雛形: run_prices_etl を実装（差分判定、バックフィル、jquants_client を用いた取得と保存の呼び出し）。（注: run_prices_etl はファイル末尾での戻り値表記が切れている個所があり、実装の継続が想定される）

### Security
- RSS パーサーに defusedxml を使用し、XML ベースの攻撃に対処。
- RSS/HTTP 周りで SSRF 対策を各所に実装（スキーム検証、プライベートホスト検査、リダイレクト検査）。
- .env ロード時に OS 環境変数を保護する protected キー概念を導入（上書き制御）。

### Notes / Limitations
- pipeline.run_prices_etl の戻り値の記載がファイル末尾で途中となっているため、ETL の最終的な戻り値や追加の ETL ジョブ（financials, calendar）の完全な実装は今後の実装・レビューが必要。
- strategy, execution, monitoring パッケージはパッケージ構成上存在するが、現時点では実装ファイルの中身は未記載（ボイラープレート）。
- 単体テスト、統合テスト、ドキュメント（DataPlatform.md / DataSchema.md 等）に基づく追加の検証が推奨される。

---

今後のリリースでは以下を予定:
- ETL 処理の完成（financials / calendar / quality チェック統合）。
- strategy / execution 層の実装（シグナル生成・発注ロジック・kabu API 統合）。
- モニタリング・アラート（Slack 通知等）の実装。