# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

全バージョンは逆順（新しいものを上）に並べます。

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージトップレベルを定義（kabusys.__init__）し、バージョンを "0.1.0" に設定。
  - 公開モジュール一覧として ["data", "strategy", "execution", "monitoring"] を定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local ファイルおよびOS環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存せずパッケージ配布後も動作。
  - .env パーサを実装（コメント行、export プレフィックス、引用符のエスケープ、インラインコメント処理などに対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供。未設定時の必須値チェック（ValueError）と許容値検証を実装（KABUSYS_ENV, LOG_LEVEL 等）。
  - duckdb/sqlite ファイルパスはデフォルトを設定し Path オブジェクトで返却。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API から株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーションに対応）。
  - HTTP レート制御（固定間隔スロットリング）を実装し、120 req/min の制限を守る RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）を実装。
  - 401 受信時にリフレッシュトークンから id_token を自動リフレッシュして1回リトライする仕組みを導入。トークンキャッシュをモジュールレベルで管理。
  - JSON デコードエラーやネットワーク例外のハンドリングとログ出力。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE により冪等性を確保し、PK 欠損行はスキップしてログ警告を出力。
  - 数値変換ユーティリティ (_to_float, _to_int) を導入し、不正値を安全に None に変換。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news へ保存するモジュールを実装（デフォルトに Yahoo Finance のビジネスカテゴリを含む）。
  - defusedxml を使用して XML Bomb 等を防止。
  - RSS レスポンスの最大受信バイト数（10MB）制限、gzip 解凍後のサイズ検査、Content-Length の事前チェックを実装してメモリ DoS を軽減。
  - リダイレクト時の SSRF 対策（スキーム検証、ホストのプライベートアドレス検査）を実装するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）を導入。最終 URL も再検証。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）および SHA-256 からの記事ID生成（先頭32文字）を実装して冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）を実装。RFC 2822 形式の pubDate を UTC に正規化する処理を追加。
  - raw_news へのバルク INSERT（チャンク化）を INSERT ... RETURNING を使って実装し、実際に挿入された記事IDのリストを返す。トランザクションを用いたロールバック対応あり。
  - 記事と銘柄コードの紐付け処理（news_symbols）を一括挿入する内部ヘルパーを実装。銘柄抽出は4桁数字パターンに対して known_codes をフィルタリング。
  - run_news_collection を実装し、複数ソースを独立して処理（1ソース失敗しても他は継続）し、新規保存数を集計して返却。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataPlatform 設計に基づく3層（Raw / Processed / Feature）＋Execution 層のテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のDDL を実装。
  - 頻出クエリ向けのインデックス一覧を定義。
  - init_schema(db_path) によりデータベースファイルの親ディレクトリを自動作成し、全テーブル／インデックスを冪等に作成する機能を実装（":memory:" サポート）。get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL の設計に基づき、ETLResult データクラス（品質問題・エラーの集約）を導入。
  - 最終取得日の算出、テーブル存在チェック、最終日取得ユーティリティを実装。
  - 市場カレンダー参照により非営業日を最も近い営業日に調整するヘルパ（_adjust_to_trading_day）を提供。
  - run_prices_etl を実装（差分更新ロジック、backfill_days による後出し修正吸収）。jquants_client の fetch / save を利用して取得→保存を行い、取得数 / 保存数を返却する設計（id_token の注入可能性を考慮）。

### セキュリティ / 信頼性 (Security / Reliability)
- 外部通信に対する安全対策を多数実装：
  - RSS XML の安全パーシング（defusedxml）
  - SSRF 対策（スキーム限定・プライベートアドレスチェック・リダイレクト検査）
  - レスポンスサイズ制限（受信バイト数上限、gzip 解凍後の再チェック）
  - DB 操作はトランザクションで保護。INSERT ... RETURNING を使用して実際の挿入結果を正確に把握。
- J-Quants クライアントでのトークン自動リフレッシュやリトライ／バックオフにより堅牢な API 呼び出しを実現。

### テストしやすさ (Testability)
- _urlopen の差し替え（モック）を想定した設計など、ユニットテストを容易にする注入ポイントを用意。
- id_token を外部から注入できる API（fetch_* / run_prices_etl 等）を用意。

### ドキュメント / ロギング
- 各モジュールに docstring を充実させ、関数の引数・戻り値・例外等を明記。
- 操作状況や警告を記録する logging を適切に配置。

### 既知の制限 (Known limitations)
- strategy / execution / monitoring の各サブパッケージは初期骨格として存在するが、実装は本リリースで限定的（詳細実装は今後追加予定）。
- ETL の品質チェックは quality モジュールとの連携を前提としている（quality の具体的実装は別途）。

----

今後の予定（例）
- strategy と execution 層の実装拡張（シグナル生成、注文送信、ポジション管理）
- 品質チェックモジュールの実装強化（各種データ検証ルール）
- テストカバレッジ拡大と CI の整備

（必要に応じて Unreleased セクションを追加してください）