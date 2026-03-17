# CHANGELOG

すべての注目すべき変更はここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  
安定版リリースのタグ付けには semver を使用します。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基本データ収集・スキーマ・設定基盤を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を定義（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring）を __all__ で宣言。

- 環境設定・ロード機能 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env/.env.local の優先順位と OS 環境変数保護（上書き禁止）に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサーを高精度に実装（コメント行・export プレフィックス、クォート内のエスケープ処理、インラインコメントの判定など）。
  - Settings クラスを実装し、必須の設定値をプロパティ経由で提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - 環境変数バリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）、デフォルト値（API ベース URL、DB パス等）を提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants からの日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - API レート制御（固定間隔スロットリング）を実装し、120 req/min を遵守する RateLimiter を導入。
  - リトライロジックを実装（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時にリフレッシュトークンから id_token を自動更新し 1 回だけリトライする仕組みを実装（無限再帰防止）。
  - ページネーション対応で fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB への保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による冪等性を確保。
  - データ変換ユーティリティ（安全な数値変換 _to_float / _to_int）を実装。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し Look-ahead Bias 対策を考慮。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news / news_symbols 関連で保存する機能を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成することで冪等性を担保。トラッキングパラメータ除去・クエリソート等の正規化を実施。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）を実装。
  - SSRF 対策を複数実装:
    - URL スキーム検証（http/https のみ許可）
    - ホストがプライベートアドレスかどうかの検査（直接 IP / DNS 走査）
    - リダイレクト時の事前検証用ハンドラ (_SSRFBlockRedirectHandler)
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェックを導入（メモリ DoS 対策）。
  - RSS の pubDate を RFC2822 形式から UTC naive datetime に変換（失敗時は警告を出して現在時刻で代替）。
  - テキスト前処理（URL 除去、空白正規化）と、記事本文・タイトルの取り扱いを実装。
  - DB 保存はチャンク分割とトランザクションでまとめ、INSERT ... RETURNING により実際に挿入された ID を正確に取得（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ロジック（4桁数字）と既知銘柄セットに基づくフィルタリングを実装（extract_stock_codes）。
  - デフォルト RSS ソース（Yahoo ビジネス）を追加。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に基づくスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）や型チェックを付与。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成を含めた初期化を行い、冪等にテーブルを作成する API を提供。get_connection で既存 DB へ接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックを実装。差分更新の既定値やバックフィル方針（直近 N 日を再取得して後出し修正を吸収）を実装。
  - ETLResult データクラスを実装し、取得数・保存数・品質チェック結果・エラーの集約を提供。品質問題を辞書化する to_dict を提供。
  - テーブル存在チェックや最大日付取得ユーティリティを実装。
  - 市場カレンダーに基づく営業日補正ロジックを実装（_adjust_to_trading_day）。
  - raw_prices/raw_financials/market_calendar の最終取得日を返すユーティリティ（get_last_price_date 等）。
  - run_prices_etl を部分実装（差分取得→ save_daily_quotes 呼び出し、バックフィル日数サポート）。（注: pipeline の一部は今後の拡張を想定）

### セキュリティ (Security)
- XML パースに defusedxml を利用して XXE / XML Bomb 対策を実施（news_collector）。
- RSS フェッチ時の SSRF 対策を複合的に実施（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
- .env ローダーは OS 環境変数を保護する機構を備え、不用意な上書きを防止。

### 改善 (Improved)
- ネットワーク信頼性を向上（レート制御 + 再試行ロジック + 429 の Retry-After 優先処理）。
- DuckDB への書き込みを冪等化（ON CONFLICT DO UPDATE / DO NOTHING）して再実行耐性を確保。
- ニュース収集でメモリ/IO 的な DoS を防ぐための最大受信サイズチェックと gzip 解凍後のサイズ検証を追加。
- DB 書き込みをチャンク化・トランザクション化してパフォーマンスと一貫性を向上。

### 既知の制約 / 注意事項 (Known issues / Notes)
- strategy/ execution / monitoring パッケージは存在するが、現行コードベースでは実装が空（拡張ポイント）。
- run_prices_etl は差分取得と保存の主要フローを実装済みだが、品質チェック（quality モジュール連携）や calendar の先読み、その他 ETL ジョブ（financials 等）の完全連携・ロギング集約は今後の作業を想定。
- DuckDB の SQL 文中で直書きする箇所があるため、外部からの値注入に際しては SQL インジェクションにならないよう利用側で注意（現在はプレースホルダを多用）。
- news_collector の DNS 解決失敗時は安全側（非プライベート）として扱う設計。環境によっては内部ホストの判定に差異が出る可能性あり。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため破壊的変更はありません。

---

将来のリリースでは、以下の項目を想定しています:
- ETL の品質チェック統合と自動通知（Slack 連携）の実装
- strategy / execution の具体的な売買ロジックおよび発注連携
- 単体テスト・統合テストの追加、CI/CD ワークフロー定義
- ドキュメント（DataPlatform.md, API リファレンス等）の整備

--- 

参照: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/