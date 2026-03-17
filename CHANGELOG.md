# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新版: [0.1.0] - 2026-03-17

---

## [0.1.0] - 2026-03-17

### 追加 (Added)
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - プロジェクトルート判定: `.git` または `pyproject.toml` を探索
  - .env パースロジックを実装（export プレフィックス対応、クォートやコメント処理を考慮）
  - 必須環境変数取得ヘルパー `_require`
  - Settings クラスを提供（プロパティ経由で取得）
    - 主な環境変数:
      - JQUANTS_REFRESH_TOKEN (必須)
      - KABU_API_PASSWORD (必須)
      - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN (必須)
      - SLACK_CHANNEL_ID (必須)
      - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
      - SQLITE_PATH (デフォルト: data/monitoring.db)
      - KABUSYS_ENV (development|paper_trading|live。デフォルト: development)
      - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト: INFO)

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本 API 呼び出しラッパー `_request` を実装
    - ベースURL: https://api.jquants.com/v1
    - レート制限: 120 req/min を固定間隔スロットリングで遵守（_RateLimiter）
    - リトライロジック: 指数バックオフ、最大 3 回（ネットワーク系/指定ステータスでリトライ）
    - 401 時の自動トークンリフレッシュ（1回のみリトライ）
    - JSON デコード失敗時の明示的エラー
    - ページネーション対応（pagination_key の追従）
  - 認証ヘルパー: `get_id_token`
  - データ取得関数を実装
    - `fetch_daily_quotes`（株価日足、ページネーション対応）
    - `fetch_financial_statements`（四半期財務データ、ページネーション対応）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する関数を実装
    - `save_daily_quotes`（raw_prices、ON CONFLICT DO UPDATE）
    - `save_financial_statements`（raw_financials、ON CONFLICT DO UPDATE）
    - `save_market_calendar`（market_calendar、ON CONFLICT DO UPDATE）
  - データの取得時刻（fetched_at）を UTC で記録して、Look-ahead bias の追跡を可能に

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装
    - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ
    - RSS 取得: `fetch_rss`
      - defusedxml を利用して XML 関係の脆弱性を低減
      - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10 MB)
      - gzip 圧縮対応と Gzip-bomb 対策（解凍後もサイズ検査）
      - SSRF 対策
        - URL スキーム検証（http/https のみ）
        - リダイレクト時にスキーム・ホストを検証するカスタムハンドラ
        - プライベート/ループバック/リンクローカル/マルチキャスト IP のアクセス拒否
      - トラッキングパラメータ（utm_* 等）を除去して URL 正規化
      - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
      - テキスト前処理（URL 除去、空白正規化）
    - DB 保存:
      - `save_raw_news`：チャンク挿入 + トランザクション、INSERT ... RETURNING で実際に挿入された ID を取得
      - `save_news_symbols` / `_save_news_symbols_bulk`：記事と銘柄コードの紐付けをチャンク挿入で保存（ON CONFLICT DO NOTHING、RETURNING により実際に挿入された件数を返す）
    - 銘柄コード抽出: 正規表現で4桁数字を抽出し known_codes に照合する `extract_stock_codes`
    - 統合ジョブ `run_news_collection` を追加（各ソースごとに独立したエラーハンドリング、銘柄紐付けを一括挿入）

- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層＋実行層に対応したテーブル定義を追加
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 推奨インデックスを定義
  - `init_schema(db_path)` によりディレクトリ作成→テーブル/インデックス作成を行う（冪等）
  - `get_connection(db_path)` を提供（初期化は行わない）

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL 結果を表す `ETLResult` データクラスを追加（品質問題・エラー集約、辞書化メソッドあり）
  - DB の最終取得日取得ユーティリティ (`get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`)
  - 営業日調整ヘルパー `_adjust_to_trading_day`
  - 差分更新方針を実装
    - デフォルトのバックフィル日数: 3 日
    - 市場カレンダー先読み 90 日、J-Quants データ開始日 2017-01-01 の定義
  - 個別 ETL ジョブ (例: `run_prices_etl`) の雛形を実装（差分算出、fetch→save のワークフロー）

- 汎用ユーティリティ
  - 型安全な変換ヘルパー `_to_float` / `_to_int`
  - テキスト前処理 `preprocess_text`
  - RSS 日時パース `_parse_rss_datetime`

### セキュリティ (Security)
- ニュース収集における SSRF 対策を強化
  - リダイレクト先の事前検査、プライベート IP の拒否
  - URL スキーム制限（http/https）
- XML パースに defusedxml を使用して XML 関連の攻撃を軽減
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の問題 (Known issues)
- run_prices_etl の戻り値
  - 現状の実装では `run_prices_etl` の最後の return 文が取得件数だけを返す形になっており、本来期待される (fetched_count, saved_count) のタプルが正しく返っていません。リリース後に修正が必要です。
- モジュール依存に関する注意点
  - pipeline モジュールは `kabusys.data.quality` を参照しているが、本 changelog の元になったコードスニペット内に quality モジュールの実装は含まれていません。実運用では quality モジュールが必要です。
  - パッケージ __all__ に "monitoring" が含まれるが、提供されたコード内に監視用モジュールの実実装が含まれていないため、インポート前提ならば追加実装が必要です。
- schema/DDL のストロングチェック
  - DDL にチェック制約等を多く含むため、DuckDB のバージョン差や SQL 実装差異によっては動作確認が必要です。

### ドキュメント/運用メモ
- 環境変数の主な必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- J-Quants のレートリミット（120 req/min）を内部で遵守するため、バッチ運用時は想定通りのスループットで動作することを確認してください。

---

今後のリリースでの予定（例）
- run_prices_etl の戻り値バグ修正
- pipeline の品質チェックモジュール（quality）実装と統合
- monitoring モジュールの追加実装（Slack 連携等）
- テストカバレッジの拡充（ネットワーク/SSRF/巨大レスポンスなどの単体テスト）

もし CHANGELOG に追記してほしい特定の項目（日付や担当者、リリース手順など）があれば教えてください。