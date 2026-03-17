CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このファイルはコードベースから推測して作成した変更履歴です。

フォーマット:
- Added: 新規機能
- Changed: 変更点（互換性に注意）
- Fixed: バグ修正
- Security: セキュリティに関する注記
- Internal: 実装上の注記・公開 API

[Unreleased]
-------------

（未リリースの変更はここに記載）

0.1.0 - 2026-03-17
------------------

Added
- 初回リリースを実装。
- パッケージ概要
  - kabusys: 日本株自動売買システムの基盤ライブラリ（__version__ = 0.1.0）。
  - モジュール分割: data, strategy, execution, monitoring を想定したパッケージ構成。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml を基準に検索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内部のエスケープ処理、インラインコメント処理（クォート無い場合の # 判定ルール）。
    - ファイル読み込み失敗時はワーニングを発行して継続。
  - Settings クラス（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - env（development/paper_trading/live）や log_level の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 提供機能:
    - 株価日足（OHLCV）取得: fetch_daily_quotes（ページネーション対応）。
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements（ページネーション対応）。
    - JPX マーケットカレンダー取得: fetch_market_calendar。
    - 認証トークン取得: get_id_token（リフレッシュトークンから POST）。
  - ネットワーク/信頼性:
    - レート制御: 固定間隔スロットリングによる 120 req/min の制限管理（_RateLimiter）。
    - リトライ: 指数バックオフ付き最大 3 回（対象: 408/429/5xx、およびネットワークエラー）。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ、再帰防止ロジックあり）。
    - ページネーションの pagination_key を追跡して多ページ取得を処理。
  - データ保存（DuckDB）用ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar:
      - fetched_at を UTC で記録（Look-ahead bias のトレース目的）。
      - 入力データの型変換ユーティリティ（_to_float, _to_int）。
      - 冪等性: INSERT ... ON CONFLICT DO UPDATE による上書き保存。
      - 主キー欠損レコードはスキップしワーニングを出力。
  - 実装上の注意:
    - モジュールレベルで ID トークンをキャッシュしページネーション間で共有。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集し raw_news に保存するパイプラインを実装。
  - 主要機能:
    - fetch_rss: RSS 取得とパース（defusedxml を利用して XML 攻撃を低減）。
    - preprocess_text: URL 除去と空白正規化。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid, など）削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
    - 記事 ID: 正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - SSRF 対策:
      - 取得前にホストがプライベートアドレスかを判定して拒否。
      - リダイレクト時にスキームとリダイレクト先のホストを検査するカスタムハンドラを使用。
    - レスポンス長制限: MAX_RESPONSE_BYTES（10MB）を超える場合は取得を中止（gzip 解凍後もチェック）。
    - save_raw_news: チャンク挿入（_INSERT_CHUNK_SIZE）かつトランザクション制御、INSERT ... ON CONFLICT DO NOTHING RETURNING を使用して新規挿入IDを正確に取得。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING RETURNING を利用）。
    - extract_stock_codes: テキストから 4 桁の銘柄コード候補を抽出し、既知コードセットに基づき有効なコードのみ返す。
    - run_news_collection: 複数ソースを横断して収集・保存・銘柄紐付けを実行。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層設計を反映した DDL を実装。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - データ整合性: 主キー・チェック制約・外部キーを広く定義。
  - インデックス: 頻出クエリ向けのインデックス定義を追加（例: code/date 検索や status 検索）。
  - init_schema(db_path) と get_connection(db_path) を提供。init_schema は親ディレクトリ作成や全DDLの冪等実行を行う。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計と差分更新機能を実装。
  - ETLResult dataclass による結果集約・to_dict 出力。品質チェック結果（quality.QualityIssue 期待）を格納可能。
  - 差分更新:
    - raw_prices, raw_financials, market_calendar の最終取得日照会ユーティリティ（get_last_price_date 等）。
    - run_prices_etl: 最終取得日からの差分/バックフィル（backfill_days デフォルト 3）を自動算出。
    - 市場カレンダー事前取得のための _CALENDAR_LOOKAHEAD_DAYS（90 日）定義。
  - 品質チェック（quality モジュール）との連携を想定（欠損・スパイク・重複・日付不整合の検出設計）。

Security
- RSS パースに defusedxml を利用し XML ベースの攻撃に備えている。
- RSS 取得時の SSRF 対策を多数実装:
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベート/ループバック/リンクローカルの場合は拒否。
  - リダイレクト先も検査して内部ネットワーク到達を防止。
- レスポンスの最大読み取りサイズを設定（MAX_RESPONSE_BYTES）し、メモリ DoS を軽減。
- .env 読み込みは protected 変数セットを使い OS 環境変数の不意な上書きを防止。

Performance
- J-Quants API 呼び出しに固定間隔スロットリングを導入（120 req/min）してレート制限を厳守。
- API 呼び出しはページネーション対応かつ ID トークンをページ間でキャッシュして効率化。
- ニュース保存はチャンク挿入と単一トランザクションでオーバーヘッドを低減。
- DuckDB の ON CONFLICT を活用し冪等性を保ちながら更新を効率的に行う。

Internal
- 型安全性・堅牢性を重視:
  - _to_float / _to_int による安全な数値変換実装（不正な小数文字列は None を返す等のルール）。
  - 日時は fetched_at を UTC で記録（ISO 8601 Z 表記）。
- ロギングを多用して運用時の可観測性を確保（info / warning / exception）。
- テスト補助のために _urlopen や id_token 注入可能な設計を採用（モック差し替えが容易）。

Breaking Changes
- 初回リリースのため該当なし。

Known limitations / TODO
- quality モジュールの詳細は本コードベースに含まれていない（外部実装との連携を想定）。
- strategy / execution / monitoring パッケージの実装はスケルトンまたは未実装（ディレクトリ存在のみ）。

参考: 公開 API（主なエントリ）
- settings: kabusys.config.settings
- DB 初期化/接続: kabusys.data.schema.init_schema, kabusys.data.schema.get_connection
- J-Quants: kabusys.data.jquants_client.get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
- News: kabusys.data.news_collector.fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- ETL: kabusys.data.pipeline.run_prices_etl, ETLResult, get_last_price_date 等

以上。