# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般ルール:
- バージョンはセマンティックバージョニングを採用します。
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装しました。
主要な追加点と設計・実装上の注目点を以下に示します。

### 追加 (Added)
- パッケージ構成
  - 基本パッケージ: kabusys（`src/kabusys`）
  - サブパッケージ/モジュール:
    - config: 環境変数・設定管理（`kabusys.config`）
    - data: データ取得・保存・ETL関連（`kabusys.data`）
      - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得）
      - news_collector: RSS からのニュース収集・前処理・DB保存
      - schema: DuckDB スキーマ定義・初期化
      - pipeline: ETL / 差分更新ロジック、ETL 結果オブジェクト等
    - strategy, execution, monitoring: プレースホルダの __init__（拡張用）
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 環境設定（kabusys.config.Settings）
  - .env ファイルまたは環境変数から設定を読み込み
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）
  - 自動ロード順序: OS環境変数 > .env.local > .env
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 必須設定取得メソッド（未設定時は ValueError を発生）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パス設定: DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）、SQLITE_PATH
  - 環境種別検証: KABUSYS_ENV（`development`, `paper_trading`, `live`）
  - ログレベル検証: LOG_LEVEL（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ `_request` 実装:
    - レート制限: 固定間隔スロットリング（120 req/min）
    - リトライロジック: 指数バックオフ、最大3回（408, 429, 5xx をリトライ対象）
    - 429 の場合は `Retry-After` ヘッダを優先
    - 401 受信時は自動でトークンをリフレッシュして1回リトライ（無限再帰を防止）
    - JSON デコードエラー時に詳細メッセージを投げる
  - IDトークンキャッシュと取得関数 `get_id_token`
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ加工ユーティリティ: `_to_float`, `_to_int`
  - データ取得時に `fetched_at` を UTC で記録（Look-ahead Bias 対策）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事整形パイプライン:
    - fetch_rss: RSS 取得・XML パース（defusedxml 使用）
    - preprocess_text: URL 除去・空白正規化
    - 正規化 URL と記事 ID 生成（SHA-256 の先頭32文字）
    - トラッキングパラメータ除去（utm_*, fbclid, gclid 等）
    - 受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再検査（Gzip bomb 対策）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストか検査し拒否
      - リダイレクト時に新URLの検査を行うカスタム RedirectHandler を使用
    - XML パース失敗時は警告ログを出して空リストを返す
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて実際に挿入された記事IDを返す（チャンク分割、単一トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING 1）
  - 銘柄抽出:
    - extract_stock_codes: 4桁数字パターンから known_codes に存在する銘柄だけを抽出（重複除去）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル群を定義した DDL を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path): DB ファイル親ディレクトリを自動作成してテーブル/インデックスを作成（冪等）
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass による結果集約（品質問題やエラー一覧を保持）
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _get_max_date / _table_exists
  - 市場カレンダー考慮の調整ロジック: _adjust_to_trading_day
  - run_prices_etl: 差分更新（最終取得日 - バックフィル）を自動算出して J-Quants から取得・保存
    - backfill_days による後出し修正吸収（デフォルト 3 日）
  - 設計上、id_token 注入可能でテストしやすい構造

### 修正 (Changed)
- .env パーサーの堅牢化:
  - `export KEY=val` 形式に対応
  - クォート内のバックスラッシュエスケープ処理、対応する閉じクォートまでを正しく扱う
  - クォートなし値のインラインコメント判定ルールを実装
  - 無効行・キー欠損時のスキップ

### セキュリティ (Security)
- RSS XML 処理に defusedxml を使用して XML bomb 等の攻撃に対処
- RSS フェッチでの SSRF 対策:
  - スキーム検査、プライベートアドレス検出、リダイレクト時の検査を実装
  - ローカルリソース（file:,ftp:,mailto: 等）を拒否
- レスポンスサイズ検査によりメモリ DoS / Gzip bomb 対策を実施
- 外部 API での認証トークンの自動更新時に無限再帰を防ぐフラグ (`allow_refresh=False`) を導入

### パフォーマンス (Performance)
- レート制限を固定間隔で実装し API 連続呼び出しのスロットリングを行う
- DB 保存はチャンク化・トランザクションまとめでオーバーヘッドを削減
- DuckDB での ON CONFLICT を活用した冪等保存によりフル再ロードを避ける

### テスト容易性 (Other)
- `_urlopen`、`_get_cached_token` 等は内部実装を差し替え可能（モック可能）に設計し、単体テストを容易化
- jquants_client の `_request` は id_token を引数注入できるため、外部依存を切り離してテスト可能

### 既知の制約 / 注意点 (Known issues / Notes)
- pipeline.run_prices_etl の戻り値のタプル作成がコード末尾で途中となっている箇所があり（末尾カンマの不整合に見える）、実装の続きが必要（コード生成時の切り落としによるものの可能性）。運用前に該当関数の完全な戻り値/呼び出し側を確認してください。
- strategy / execution / monitoring はまだ実装エントリのみ（拡張ポイント）。

## 今後の予定 (Unreleased / Roadmap)
- run_prices_etl の完遂と他 ETL ジョブ（財務、カレンダー、ニュース統合）の追加実装完了
- 品質チェックモジュール（kabusys.data.quality）の実装と ETL への統合
- 発注実装（kabu ステーション API 経由）の execution モジュール実装
- Slack 通知などの運用監視機能を monitoring モジュールに追加
- CI / テスト（単体・統合）とドキュメントの整備

---

もし CHANGELOG に追記してほしい詳細（例: リリース日を別に設定、特定のリファクタ/コミット記載、レビュ担当者や関連Issue番号など）があれば教えてください。