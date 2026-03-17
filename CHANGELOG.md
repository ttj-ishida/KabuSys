# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

※この CHANGELOG はコードベース（src/kabusys 以下）の内容から推測して作成しています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォーム KabuSys のコア基盤を実装しました。以下の主要コンポーネントと機能を含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。バージョンは `0.1.0`。
  - __all__ に data, strategy, execution, monitoring を設定。

- 環境設定モジュール (kabusys.config)
  - .env / .env.local または環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パーサ：コメント、`export ` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - .env の上書き制御（override）と OS 環境変数保護（protected）機能。
  - Settings クラスを提供し、主要設定プロパティを公開:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`（必須）
    - DB パス: `duckdb_path`（デフォルト: data/kabusys.duckdb）, `sqlite_path`（デフォルト: data/monitoring.db）
    - 実行環境/ログレベル: `env`（validation: development/paper_trading/live）, `log_level`（validation）
    - 環境判定ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - 株価日足（OHLCV）取得: fetch_daily_quotes (ページネーション対応)
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements (ページネーション対応)
    - JPX マーケットカレンダー取得: fetch_market_calendar
    - リフレッシュトークンからの ID トークン取得: get_id_token
  - 信頼性・運用面の設計:
    - API レート制限を厳守する固定間隔レートリミッタ（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータスコードに 408, 429 を含む。500 系は再試行対象。
    - 401 受信時はトークンを自動リフレッシュして最大 1 回リトライ（無限再帰回避ロジックあり）。
    - ページネーション間で共有するモジュールレベルのトークンキャッシュを提供。
  - データ保存（DuckDB 連携、冪等性）:
    - save_daily_quotes / save_financial_statements / save_market_calendar により raw_* テーブルへ保存（ON CONFLICT DO UPDATE を利用）。
    - レコードの PK 欠損行はスキップして警告ログを出力。
    - fetched_at を UTC ISO 形式で記録し、データ取得時刻をトレース可能に（Look-ahead Bias 対策）。
  - ユーティリティ: 型変換ヘルパー `_to_float`, `_to_int`（不正値は None へ）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集と raw_news / news_symbols への保存ワークフローを実装。
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 防御）。
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホストのプライベート/ループバック/リンクローカル判定（IP 直接判定と DNS 解決）。
    - リダイレクト検査用カスタムハンドラを使用してリダイレクト先も検証。
    - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent 指定、Content-Length の事前チェック。
  - データ処理:
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）、SHA-256(先頭32文字) による記事ID生成で冪等性保証。
    - テキスト前処理: URL 除去、空白正規化。
    - pubDate の RFC 形式パース（UTC へ正規化、失敗時は現在時刻で代替）。
    - raw_news 保存: チャンク化して INSERT ... RETURNING を利用、新規挿入ID一覧を正確に返却。全件をトランザクション内で処理。
    - news_symbols（記事-銘柄紐付け）保存: INSERT ... RETURNING を使用し挿入数を返却。_bulk 関数で複数記事分を一括保存。
  - 銘柄抽出: 正規表現で 4 桁数字を抽出し、known_codes に含まれるもののみ採用（重複除去）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤを定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed Layer。
  - features, ai_scores を含む Feature Layer。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution Layer。
  - 各テーブルに適切な型チェック制約（CHECK）、主キー、外部キー制約を設定。
  - クエリパフォーマンス向上のためのインデックス群を定義。
  - init_schema(db_path) により冪等にスキーマを作成し DuckDB 接続を返却。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult データクラス（品質問題・エラー情報の保持、辞書化機能）。
  - 差分更新を扱うユーティリティ:
    - テーブル存在チェック、最大日付取得ヘルパー、営業日調整ロジック（market_calendar を参照して過去の最も近い営業日に調整）。
    - 最終取得日ベースの差分再取得ロジック（デフォルトの backfill_days = 3）。
    - get_last_* ヘルパー関数（raw_prices, raw_financials, market_calendar）。
  - 個別 ETL ジョブ（run_prices_etl を含む）: 差分取得 → jquants_client で保存 → 保存件数を返すワークフロー（run_prices_etl の一部が実装済み）。

- パッケージ構成
  - data パッケージに複数のサブモジュール（jquants_client, news_collector, schema, pipeline）を実装。
  - strategy / execution パッケージの雛形を追加（__init__.py が存在）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用して XML 攻撃に対処。
- RSS フェッチで SSRF 対策を多数導入（スキーム検証、プライベートアドレス検出、リダイレクト時の再検証）。
- レスポンスサイズ上限・gzip 解凍後サイズチェックによりメモリ DoS を緩和。

### ドキュメント / 開発者向けメモ (Notes)
- .env の自動読み込みはプロジェクトルート発見に依存するため、配布後やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- J-Quants の ID トークンはモジュールレベルでキャッシュされ、ページネーション間で共有される（force_refresh オプションあり）。
- DuckDB スキーマは init_schema で冪等に作成されるため、マイグレーションが必要な場合は別途対応が必要。
- news_collector の HTTP 接続部分は `_urlopen` をモックしてテスト容易化が想定されている。
- strategy / execution の実装は雛形のみで、実際の取引ロジック・発注フローは今後の実装課題。

### 既知の制限 / TODO
- pipeline.run_prices_etl の戻り値の形（コード提供分の末尾で切れている部分）など、まだ未完成/拡張が必要な箇所がある可能性がある（実装の続きが必要）。
- strategy / execution の具体的な実装は含まれていない（将来的に戦略モジュールと発注実装を追加予定）。
- 単体テスト、統合テスト、CI 設定はコードからは推測できないため、適切なテストスイートの整備が推奨される。

---

この CHANGELOG はコードベースの実装内容をもとに推測して作成しています。追加のコミット履歴やリリースノートがある場合は、それらに合わせて更新してください。