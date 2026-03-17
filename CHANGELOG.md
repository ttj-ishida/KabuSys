# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-17

最初の公開リリース（初期実装）。主要な機能・設計方針、セキュリティ対策、データ永続化スキーマ、ETL パイプライン等を含む。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys。トップレベル __version__ = "0.1.0" を含む（src/kabusys/__init__.py）。
  - サブモジュールの雛形: data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env パーサー実装:
    - コメント行、export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等の取り扱いに対応。
    - override / protected オプションを用いた .env の安全な読み込み。
  - 環境変数の必須チェック (_require) と Settings クラスを提供:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティ。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得対象:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー。
  - 設計上の特徴:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークン経由で id_token を自動更新して 1 回リトライ。
    - fetched_at を UTC で記録していつデータを取得したかをトレース可能にする（Look-ahead Bias 対策）。
    - DuckDB への保存は ON CONFLICT DO UPDATE を用いて冪等性を確保。
  - 公開関数:
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（厳密な int 変換ロジックを含む）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存する機能を実装。
  - 設計上の特徴:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - 受信データサイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 防止。
    - gzip 圧縮対応と解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、query ソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - SSRF 対策: URL スキーム検証、プライベート/ループバック/リンクローカルアドレス判定、リダイレクト先の事前検証（カスタム RedirectHandler）。
    - コンテンツ前処理（URL 除去・空白正規化）。
  - DB への保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返却。トランザクションでまとめる。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING を使って実行。
  - 銘柄コード抽出ロジック:
    - 4桁数字パターン（\b(\d{4})\b）を抽出し、与えられた known_codes に含まれるもののみを返す。

- DuckDB スキーマと初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく多層テーブル定義を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) によるディレクトリ自動作成と DDL 実行、get_connection() を提供。

- ETL / データパイプライン (src/kabusys/data/pipeline.py)
  - 差分更新ベースの ETL 設計:
    - DB 側の最終取得日を確認して差分のみ取得、backfill_days による後出し修正吸収。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）。
    - 品質チェックモジュール（quality）との連携設計（品質問題は収集継続、呼び出し元が判断）。
  - ETLResult dataclass により処理結果と品質問題・エラーを集約・シリアライズ可能に。
  - ヘルパー実装:
    - テーブル存在チェック、最大日付取得、トレーディングデイへの調整関数。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 個別ジョブ:
    - run_prices_etl: 差分取得→jq.fetch_daily_quotes→jq.save_daily_quotes を実行する処理を実装（差分計算・バックフィル対応）。

### セキュリティ (Security)
- SSRF 対策を複数導入（news_collector）:
  - URL スキーム制限（http/https のみ）。
  - リダイレクト先のスキームとホストチェック（_SSRFBlockRedirectHandler）。
  - プライベート/ループバック/リンクローカル/マルチキャストの判定による接続拒否。
- XML パースで defusedxml を使用し、外部脆弱性を緩和。
- .env 読み込み時に OS 環境変数を保護する protected 機能を提供。

### 既知の問題 (Known issues)
- run_prices_etl の実装においてソースの抜粋段階で return 文が不完全に見える（ファイル末尾で "return len(records), " のような途中終了が確認できる）。実際の戻り値や後続の financials / calendar ETL 等の統合は未完成の可能性があるため、呼び出し時には注意が必要。
- strategy と execution パッケージは __init__ が存在するのみで具体的実装は含まれていない（プレースホルダ）。
- テスト・例外パスの網羅（外部 API のモックやエラーハンドリングの統合テスト）が不足している可能性がある。

以上がコードベースから推測される初期リリースの変更履歴です。不足・修正事項やリリースノートの調整が必要であれば、目的（利用者向け、開発者向け、リリース投稿向け）に合わせて文章を調整します。