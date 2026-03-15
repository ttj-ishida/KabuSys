# Changelog

すべての注目すべき変更点はここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-15

最初の公開リリース。日本株自動売買システム "KabuSys" の基盤モジュール群を実装しました。主要な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基本情報
  - パッケージルート: kabusys、バージョン __version__ = "0.1.0" を設定。
  - モジュール構成のスケルトンを追加: data, strategy, execution, monitoring パッケージを公開。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーを実装:
    - コメント行、`export KEY=val` 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - .env の上書き制御（override）や OS 環境変数を保護する protected セットを実装。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能にした（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル等）。
    - 環境値の検証: KABUSYS_ENV（development, paper_trading, live）、LOG_LEVEL（DEBUG, INFO, ...）のチェックとエラー通知。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本的な API クライアントを実装。
  - 取得機能:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）(fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
    - ページネーション対応（pagination_key を用いたループ）
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token を実装。
    - モジュール内で ID トークンをキャッシュし、ページネーション間で共有。
    - 401 受信時はトークンを自動リフレッシュして 1 回のみリトライするロジックを実装（無限再帰防止措置あり）。
  - HTTP リクエストの堅牢化:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）に対するリトライ、429 の場合は Retry-After ヘッダを尊重。
    - タイムアウトや JSON デコード失敗時のエラーハンドリング。
  - ロギングによる取得件数・警告の出力。

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - DataPlatform 設計に基づく 3 層＋実行層のスキーマ DDL を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに妥当性チェック（CHECK 制約）や主キー、外部キーを設定。
  - パフォーマンスを考慮したインデックス定義を多数追加（銘柄×日付スキャン、状態検索、JOIN 支援など）。
  - init_schema(db_path) を提供して DuckDB ファイルの親ディレクトリ作成とテーブル／インデックスの冪等的作成を行う。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- DuckDB への保存ユーティリティ（jquants_client 側）
  - fetch_* の結果を DuckDB に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装。
  - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で既存データを更新可能。
  - PK 欠損行のスキップとその警告ログ出力。
  - fetched_at を UTC タイムスタンプとして記録し、Look-ahead Bias を防止する設計。

- データ変換ユーティリティ
  - _to_float: 空値や変換失敗時に None を返す。
  - _to_int: "1.0" のような float 文字列は float 経由で変換し、小数部が 0 以外なら None を返す等の厳密な変換ロジックを提供。

- 監査ログ・トレーサビリティ (`kabusys.data.audit`)
  - 戦略→シグナル→発注要求→約定に至る監査テーブル群を実装:
    - signal_events, order_requests, executions
  - 設計方針の反映:
    - order_request_id を冪等キーとして扱うチェック、ステータス遷移用の ENUM 風文字列制約、created_at/updated_at のタイムスタンプ保存。
    - すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
    - FK は削除制限（ON DELETE RESTRICT）により監査ログを保持。
  - 監査用インデックスを複数追加（signal_id / strategy / status / broker_order_id 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し既存の DuckDB 接続へ監査テーブルを追加。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の制約・注意点 (Notes)
- J-Quants API トークン取得や各種 API 呼び出しはネットワークや認証情報に依存するため、本リリースでは外部サービスの実環境での追加検証が必要です。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布形態やインストール先によって挙動が変わる可能性があります。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- DuckDB スキーマは初期化時に既存テーブルに対して冪等に実行される設計ですが、将来的なスキーママイグレーション機能は未実装です。

今後の予定（例）
- execution / strategy 層の具体的な実装（発注ドライバ、ブローカーインターフェース、リスク管理等）
- モニタリング / アラート機能（Slack 通知の実装）
- スキーマのバージョン管理およびマイグレーション機能

---

（注）この CHANGELOG は提供されたコードベースから推測して作成したものであり、実際のコミット履歴やリリースノートと完全に一致しない場合があります。