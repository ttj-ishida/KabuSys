# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]
- なし（次回リリースに向けた開発項目・未定義の修正を記載してください）

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0" を設定。
  - モジュール公開API: data, strategy, execution, monitoring を __all__ で定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml）を実装し、CWDに依存しない自動.env読み込みを実現。
  - .env/.env.local の優先順位制御と上書きオプション（protectedで既存OS環境変数を保護）。
  - .env行パーサ（export KEY=val、引用符処理、インラインコメント処理）を実装。
  - 必須環境変数取得用の _require と Settings クラスを実装。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト設定（DBパス、KABU API base URL、LOG_LEVEL 等）を定義。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - HTTP リクエストユーティリティを実装し、JSONデコードエラーハンドリングを追加。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。
  - 401 受信時の自動トークンリフレッシュ（1回）とモジュールレベルIDトークンキャッシュを実装。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE）。
  - 値変換ユーティリティ (_to_float, _to_int) を実装（安全な変換・空値処理）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存する一連の処理を実装。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリソートを実装。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキーム/ホスト検証ハンドラ (_SSRFBlockRedirectHandler)
    - プライベートアドレス判定（IP直接判定 + DNS解決してA/AAAAをチェック）
  - XML セキュリティ対策: defusedxml を利用して XML Bomb 等に対処。
  - レスポンスサイズ保護: MAX_RESPONSE_BYTES（10 MB）制限、gzip 解凍後も再チェック。
  - レスポンス受信時の Content-Length チェックとオーバーサイズの早期スキップ。
  - RSS パース、title/content の前処理（URL除去・空白正規化）。
  - DuckDB へバルク INSERT をチャンク化して保存（INSERT ... RETURNING を使用して実際に挿入されたID/件数を返す）。トランザクション単位で処理。
  - 銘柄コード抽出ロジック（4桁数字）と既知銘柄セットを用いたフィルタリング。
  - run_news_collection により複数RSSソースを独立して収集・保存。既知銘柄が与えられた場合は news_symbols への紐付けを実施。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層データモデルを定義する DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブルを定義。
  - features, ai_scores 等の Feature レイヤーテーブルを定義。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤーテーブルを定義。
  - 各種制約（PK/FOREIGN KEY/チェック制約）と検索頻度を考慮したインデックスを定義。
  - init_schema(db_path) でディレクトリ作成と全DDL/インデックス適用を行う初期化APIを提供。
  - get_connection(db_path) で既存DBへの接続を提供。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を意識した ETL フローを実装（最終取得日を基に差分を算出）。
  - デフォルトで backfill_days により過去数日を再取得してAPI後出し修正を吸収（デフォルト 3日）。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90 日）概念を導入。
  - ETLResult dataclass により ETL の取得/保存件数、品質問題、エラーを集約して返却。
  - テーブル存在チェック、最大日付取得ユーティリティを提供。
  - run_prices_etl の骨組みを実装（fetch + save の流れ）。差分計算、最小データ開始日の考慮（2017-01-01）。

### 改善 (Changed)
- 全体
  - 各モジュールに詳細な設計コメントと安全性・冪等性に関する方針を追加（設計原則・考慮点の明文化）。
  - ロギングを適切な箇所に配置し、処理状況や警告を出力するようにした。

### セキュリティ (Security)
- 外部入力（RSS, URL）に対する多層防御を実装（defusedxml, SSRF防止, レスポンスサイズ制限）。
- .env 読み込みは既存OS環境変数を保護（protected set）して上書きを制限。

### 既知の制限・注意点 (Known issues / Notes)
- J-Quants API のレート制限を尊重する設計だが、運用環境でのスループット要件に応じた調整が必要となる可能性がある（現在は固定 120 req/min）。
- get_id_token は settings.jquants_refresh_token に依存するため、本番では適切なシークレット管理が必要。
- news_collector のホスト名 DNS 解決失敗は「安全側（非プライベート）」として扱って接続を許可する実装になっている（運用環境では監視を推奨）。
- run_prices_etl の戻り値や処理フローは継続的拡張を想定して一部骨組みのみを実装（例: quality チェックの取り込み箇所）。

### 破壊的変更 (Breaking Changes)
- なし（初版リリース）

### 開発者 / コントリビューション
- 初期リリースに含まれる機能は将来的に拡張・リファクタリングを予定。外部APIキーやDBスキーマの変更はリリースノートで明示します。

---

この CHANGELOG はコードベースから推測して作成したため、実際のコミット履歴とは差異がある可能性があります。必要であれば、実際の git 履歴やリリース計画に沿って内容を調整します。