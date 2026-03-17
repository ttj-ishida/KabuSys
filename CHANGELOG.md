# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

※この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - サブパッケージを公開: data, strategy, execution, monitoring。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local をロード（配布後も動作する探索方式）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサーは export KEY=val 形式、クォート文字列、インラインコメント、エスケープを適切に処理。
    - .env の上書き制御（override）と OS 環境変数保護（protected set）をサポート。
  - 型安全な Settings クラスを提供し、アプリで必要な設定値（J-Quants / kabu / Slack / DB パス / 環境名 / ログレベル等）をプロパティ経由で取得。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）および便宜的プロパティ（is_live / is_paper / is_dev）を追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用の API クライアントを実装。
  - レート制限管理：120 req/min を守る固定間隔スロットリング（RateLimiter）。
  - 再試行（リトライ）ロジック：指数バックオフ、最大試行回数、HTTP 408/429/5xx の再試行をサポート。429 の場合は Retry-After を優先。
  - 認証トークンキャッシュと自動リフレッシュ：
    - get_id_token() を用いたリフレッシュトークンからの ID トークン取得。
    - 401 を検出した場合はトークンを1回だけ自動リフレッシュしてリトライ。
  - ページネーション対応の取得関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除し、fetched_at を記録して Look-ahead Bias のトレースを可能に。
  - データ整形ユーティリティ（数値変換の安全処理 _to_float / _to_int）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集して raw_news に保存するエンドツーエンド機能を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策：URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（IP直接判定＋DNS解決による A/AAAA レコード検査）、リダイレクト時の検査用ハンドラ実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の上限検査（Gzip bomb 対策）。
    - 許可されていないスキーム・プライベートアドレスは取得をスキップしログ出力。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去してクエリをソート、フラグメント削除。正規化後の URL を SHA-256（先頭32文字）で記事IDを生成し冪等性を確保。
  - テキスト前処理：URL 除去、連続空白正規化など。
  - DB 保存:
    - save_raw_news(): チャンク分割・1トランザクションでのバルク INSERT を行い、挿入された記事IDリストを返す（ON CONFLICT DO NOTHING）。
    - save_news_symbols() / _save_news_symbols_bulk(): 記事と銘柄コードの紐付けをバルク保存し、実際に挿入された件数を返す。
  - 銘柄抽出: 正規表現で 4 桁数字を抽出し、known_codes に基づくフィルタリング。
  - run_news_collection(): 複数 RSS ソースの収集を統合し、個々のソース失敗は他のソースに影響を与えない設計。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを定義。
  - init_schema(db_path) でディレクトリ作成→DuckDB接続→すべてのDDL/インデックスを実行して初期化するユーティリティ。
  - get_connection(db_path) で既存DBへの接続を取得するヘルパを提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行結果を表す ETLResult dataclass を実装（品質問題やエラーの集約、辞書化メソッド等）。
  - 差分更新のためのヘルパ群を実装（テーブル存在チェック、最終取得日の取得、営業日調整）。
  - run_prices_etl(): 差分更新ロジック（最終取得日に基づく date_from 自動算出、backfill による後出し修正吸収）、J-Quants からの取得→保存の流れを実装。
  - 市場カレンダーの先読みを考慮する設計や、品質チェックモジュールとの連携を想定した構成。

### セキュリティ (Security)
- RSS 収集処理において SSRF 対策と XML/圧縮攻撃対策を実装。
- .env 読み込みは OS 環境変数保護の仕組みを備え、意図しない上書きを防止。

### パフォーマンス (Performance)
- API 呼び出しに RateLimiter を導入してレート制限を厳守。
- DB バルク挿入はチャンク処理・トランザクションにまとめることでオーバーヘッドを削減。
- ページネーション処理でモジュールレベルの token キャッシュを再利用し効率化。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の戻り値（ドキュメント上は (取得数, 保存数) を返す想定）について、現状の実装は末尾が途中で切れているように見える（戻り値の構築が不完全な可能性）。リリース直後はこの部分の挙動確認が推奨されます。
- schema/init の DDL はチェック制約等を多く含むため、既存データとの互換やマイグレーションは慎重に行ってください。
- J-Quants API のレート制限やリトライポリシーは実運用時の負荷や API の仕様変更によりチューニングが必要になる場合があります。
- news_collector の _is_private_host() は DNS 解決失敗時に安全側（非プライベート）とみなす実装のため、環境によっては追加検査が必要なケースがあります。

---

今後の予定（例）
- run_prices_etl の戻り値/エラーハンドリングの修正。
- pipeline の品質チェック連携（quality モジュールの具体実装反映）。
- strategy / execution / monitoring サブパッケージの実装拡充と統合テスト。

--- 

翻訳上・推測に基づく記述が含まれます。実際の変更履歴に合わせて必要に応じて修正してください。