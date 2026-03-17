CHANGELOG
=========

すべての変更は Keep a Changelog に準拠しています。  
安定版リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- 作業中／未リリースの変更はありません。

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリース (0.1.0)。KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてパッケージ名とバージョンを定義（__version__ = "0.1.0"）。
  - 環境設定管理
    - src/kabusys/config.py
      - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - .env パースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント、コメント除去などに対応。
      - Settings クラスを提供し、J-Quants, kabuステーション, Slack, DBパスなどの設定をプロパティで取得。値検証（env/log level/有効値チェック）と必須環境変数未設定時の例外処理を実装。
  - データアクセス（J-Quants）
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。
      - API レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
      - 冪等性を考慮したデータ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
      - リトライロジック（最大 3 回、指数バックオフ）と 408 / 429 / 5xx のリトライ扱い。429 の Retry-After ヘッダを尊重。
      - 401 Unauthorized を検知してリフレッシュトークンで id_token を自動更新して 1 回だけリトライする仕組みを実装。
      - ページネーション対応（pagination_key を利用して全データ取得）。
      - データ取得時に fetched_at を UTC で記録し、Look-ahead Bias のトレースに対応。
      - 型安全な変換ユーティリティ (_to_float, _to_int) を実装。
  - ニュース収集
    - src/kabusys/data/news_collector.py
      - RSS フィードから記事を収集して DuckDB に保存する実装。
      - セキュリティ対策:
        - defusedxml を利用した XML パース（XML Bomb 等への耐性）。
        - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム／プライベートIP検査、初回ホストのプライベートアドレス事前検証。
        - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
        - URL 正規化時にトラッキングパラメータを除去（utm_ 等）。
      - 記事IDは正規化 URL の SHA-256 先頭32文字で生成して冪等性を確保。
      - RSS 取り込みと DuckDB 保存においてトランザクションでまとめてチャンク INSERT を行い、INSERT ... RETURNING により新規挿入数を正確に取得する。
      - 銘柄コード抽出ユーティリティ（4桁数字）と news_symbols への紐付け機能を実装。
      - 公開関数 run_news_collection により、複数ソースを個別に処理（1ソース失敗でも他を継続）し新規保存数を返す。
      - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。
  - DuckDB スキーマ
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution 層を想定した DuckDB テーブル定義を提供。
      - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed Layer。
      - features, ai_scores 等の Feature Layer。
      - signal_queue, orders, trades, positions, portfolio_performance 等の Execution Layer。
      - 主要クエリ向けのインデックス定義を追加。
      - init_schema(db_path) によりディレクトリ自動作成とテーブル／インデックス作成を行う冪等的初期化機能を提供。
      - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。
  - ETL パイプライン
    - src/kabusys/data/pipeline.py
      - ETL の方針と差分更新ロジックを実装。
      - ETLResult dataclass を追加（各種取得数、品質問題、エラー一覧、has_errors/has_quality_errors プロパティ、辞書化メソッド）。
      - DBテーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date) を実装。
      - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) を実装。
      - 差分取得用の get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
      - run_prices_etl を実装（差分範囲の算出、backfill_days による再取得、J-Quants からの取得と保存の呼び出し）。（注: コードスニペットは途中で切れているが基本ロジックは含まれる）

Changed
- 初期実装のため、既存コードとの互換性を意識した設計を採用。設計上のガイドライン（レートリミット順守、冪等性、SSRF対策、トランザクション管理等）を各モジュールで反映。

Fixed
- N/A（初回リリース）

Security
- RSS パーサで defusedxml を使用して XML に対する安全性を確保。
- ニュース取得で SSRF やローカルアドレスアクセスを防ぐためにリダイレクト時と最終 URL のチェック、DNS 解決によるプライベート IP 判定、スキーム検証を実装。
- .env 読み込みでファイル読み取り失敗時に警告を出す実装。既存 OS 環境変数を保護する protected セットを導入。

Performance
- J-Quants API 呼び出しは固定間隔スロットリングでレートを制御し、429 の場合は Retry-After を尊重して待機するようにして API レスポンスに応じたスロットリングとリトライを実現。
- ニュース保存はチャンク化して一括 INSERT を行い、SQL オーバーヘッドを削減。
- DuckDB のインデックスを追加し、銘柄×日付スキャンやステータス検索のパフォーマンスを向上。

Notes / Known limitations
- pipeline.run_prices_etl の実装スニペットはコード中で途中で終了している（掲載コードの最後が return len(records), のように不完全）。実際のリリースでは戻り値や後続処理（品質チェックや ETLResult の生成など）の完成が必要。
- J-Quants クライアントは urllib ベースの実装であり、HTTP セッションや接続プールの最適化は未実装（将来的に requests / httpx などへの移行を検討）。
- ニュースの銘柄抽出は単純な正規表現（4桁）と known_codes に依存しているため、誤検出や文脈に依る誤抽出の可能性がある。

Breaking Changes
- なし（初回リリース）

Authors
- 初期実装: コードベースに基づき推測して作成

（補足）
- 本 CHANGELOG は提示されたコード内容から機能・設計・セキュリティ対策等を推測して作成しています。実際のコミット履歴やリリースノートと合わせて調整してください。