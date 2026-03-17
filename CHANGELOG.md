# CHANGELOG

すべての重要な変更・追加点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※このCHANGELOGは、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは `0.1.0`。
  - サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export 形式やクォート付き値、行末コメントなどを考慮した .env パーサを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数取得用の `_require()` と Settings クラスを提供。以下の主要設定プロパティを実装:
    - J-Quants: jquants_refresh_token
    - kabuステーション API: kabu_api_password, kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - Slack: slack_bot_token, slack_channel_id
    - DB パス: duckdb_path (デフォルト: data/kabusys.duckdb), sqlite_path (デフォルト: data/monitoring.db)
    - 環境種別チェック: env (development/paper_trading/live)、ログレベル検証、is_live/is_paper/is_dev ヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得関数を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx を再試行対象）を実装。429 の場合は Retry-After を優先。
  - 401 発生時はリフレッシュトークンを使って id_token を自動更新して 1 回だけリトライ。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。いずれも冪等性を保証するため ON CONFLICT を使用して UPDATE を行う。
  - データ変換ユーティリティ（_to_float, _to_int）を実装。整数変換では小数部がある場合は None を返すなどの安全処理を実装。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead bias のトレースを可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードの取得と raw_news テーブルへの保存を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ）とプライベート IP/ループバック/リンクローカルを検出してアクセス拒否。
    - リダイレクト時の事前検証用ハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、gzip 解凍後もチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事ID を正規化URLの SHA-256（先頭32文字）で生成して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、新規挿入された記事ID を返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。ON CONFLICT で重複を無視し、実際に挿入された件数を返却。
  - 銘柄抽出: テキスト中の 4 桁数字候補から known_codes に含まれるものだけを抽出する extract_stock_codes を提供。
  - run_news_collection: 複数ソース（DEFAULT_RSS_SOURCES に Yahoo Finance をデフォルト）から収集し、エラー源ごとに個別にハンドリングして継続処理、最後にソース別の保存件数を返却。known_codes が与えられた場合は新規記事に対する銘柄紐付けを実行。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づいた多層（Raw / Processed / Feature / Execution）のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - 頻出クエリ用のインデックスを複数追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) により（必要に応じて親ディレクトリを作成して）すべてのテーブルとインデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得するユーティリティを提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の処理設計と一部実装。
  - ETLResult データクラス: 実行結果（取得数、保存数、品質問題、エラーリスト等）を格納・変換する API を提供。
  - スキーマ存在チェックやテーブルの最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
  - market_calendar を使ったトレーディングデー調整ヘルパー `_adjust_to_trading_day` を実装（過去方向に最大 30 日遡る）。
  - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - run_prices_etl: 株価差分 ETL を実装（差分取得、バックフィル日数のデフォルトは 3 日、最小取得開始日は 2017-01-01）。取得後に jquants_client 経由で保存し、保存件数を返却する設計（品質チェックは別モジュール quality を呼び出す想定）。

### 変更 (Changed)
- 初回リリースのため過去からの変更はありません。

### 修正 (Fixed)
- 初回リリースのため過去からの修正はありません。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、XML 関連の攻撃緩和を実装。
- RSS フェッチ時に SSRF 対策（スキーム検証、プライベートIPチェック、リダイレクト検査）を導入。
- ネットワークおよびレスポンスサイズに対する保護（タイムアウト、最大バイト読み込み、gzip 解凍後チェック）を実装。

### 既知の注意点 / 制限
- pipeline モジュール内で言及されている品質チェックモジュール (kabusys.data.quality) はコード参照時点では外部依存として想定されており、実際のチェック実装は別モジュールで提供される想定。
- 一部の HTTP リクエストで urllib を直接使用しているため、より高度なリトライやセッション管理が必要な場合は将来的に requests 等への移行を検討。
- DB の型や制約は設計段階で厳密に定められているため、外部データに想定外のフォーマットが混入した場合は保存時に None 変換やスキップが発生する（ログで警告を出力）。

### 互換性 (Compatibility)
- 初回リリースのため後方互換性に関する破壊的変更はなし。

---

(参考)
- 主な実装ファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py

もし CHANGELOG の形式や記載粒度（例えば個別コミット単位、より詳細な実装の箇条化等）を変更したい場合は指示してください。