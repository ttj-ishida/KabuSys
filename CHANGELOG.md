CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初版を公開。
  - パッケージバージョンは kabusys.__version__ = 0.1.0。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ対応、インラインコメントの処理（クォート有無に応じた挙動）などに対応。
    - 読み込み時に OS 環境変数を保護する protected 機能（.env の上書きを制御）。
  - 必須値取得時に未設定だと ValueError を送出する _require を提供。
  - 環境（development / paper_trading / live）とログレベルのバリデーションを実装。is_live / is_paper / is_dev のユーティリティプロパティを提供。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や kabu API / Slack 関連の設定プロパティを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得のための fetch_* 関数を実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリング (_RateLimiter) により 120 req/min を順守。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
  - ページネーション間で使い回すモジュールレベルのトークンキャッシュを実装。
  - DuckDB への保存関数 save_* を実装（raw_prices / raw_financials / market_calendar）。全て冪等（ON CONFLICT ... DO UPDATE）で保存。fetched_at を UTC で記録してデータ取得タイミングが追跡可能。
  - 型安全な数値変換ユーティリティ (_to_float / _to_int) を実装。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得・正規化・DB保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等に対する防御。
    - リダイレクト時にスキームとホストの検査を行うカスタム HTTPRedirectHandler(_SSRFBlockRedirectHandler) を実装し、SSRF を軽減。
    - URL スキームの検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込み時に超過チェック。gzip 解凍後もサイズ検査。
  - 記事ID は URL 正規化後の SHA-256 の先頭32文字で生成し冪等性を確保（utm_ 等トラッキングパラメータを除去して正規化）。
  - テキスト前処理 preprocess_text を実装（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news は INSERT ... RETURNING id を使用し、実際に新規挿入された記事IDを返す（チャンク挿入、1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、チャンク、トランザクション）。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と known_codes によるフィルタリング（重複除去）。
  - fetch_rss は HTTP ヘッダ（User-Agent, Accept-Encoding）対応。XML パースエラーや不正なフィードはログ出力して空リストを返す。
  - run_news_collection により複数ソースを順次処理し、ソース単位で独立したエラーハンドリングを実施。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature / Execution）に対応するテーブル群を定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 各テーブルに適切な型チェック制約・PRIMARY KEY を定義。
  - クエリパターンを考慮したインデックス群を定義（code/date 検索やステータス検索向け）。
  - init_schema(db_path) により必要な親ディレクトリ作成 → 全 DDL とインデックスを実行して DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETL の結果を表す ETLResult データクラスを追加（品質問題とエラー集約、辞書化用 to_dict）。
  - 差分更新ヘルパー: テーブル存在チェック、テーブルの最大日付取得関数 (_get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date) を実装。
  - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day を実装（最大 30 日遡りのフォールバックあり）。
  - run_prices_etl を実装（差分更新ロジック、backfill_days による再取得、jquants_client.fetch / save を組み合わせて取得→保存を実行）。ETL 設計方針として品質チェックは Fail-Fast とせず収集を継続する方針を採用。
  - jquants_client や _urlopen 等に id_token / オープナー等を注入できる設計でテスト容易性を確保。

Performance
- jquants_client のレート制御と再試行、news_collector のチャンク挿入とトランザクションまとめにより API 呼び出し回数と DB オーバーヘッドを最小化。
- news_collector のチャンクサイズと INSERT ... RETURNING により大量データ挿入時の効率化を実現。

Security
- RSS 周りで defusedxml, SSRF 検査、レスポンスサイズ制限、gzip 解凍後の検査を実装。
- .env 読み込みで OS 環境変数の保護（protected keys）を行い、環境情報の破壊的上書きを防止。

Testing / Extensibility
- jquants_client の id_token キャッシュや _request の allow_refresh フラグ、news_collector の _urlopen がモック可能（テストで差し替え可能）な設計。
- fetch_* 関数がページネーション対応でテストしやすい構成。

Fixed
- （今回の初版リリースにつき該当なし）

Changed
- （今回の初版リリースにつき該当なし）

Deprecated
- （今回の初版リリースにつき該当なし）

Removed
- （今回の初版リリースにつき該当なし）

Security
- RSS/HTTP 周りの SSRF・XML Bomb 緩和策を実装（defusedxml、リダイレクト検査、プライベートIPブロック、コンテンツ長制限）。

Notes / Known limitations
- DuckDB スキーマは初期化関数 init_schema を利用する前提。get_connection はスキーマ初期化を行わない点に注意。
- run_prices_etl 等の ETL ジョブは品質チェックモジュール (kabusys.data.quality) と連携する点が設計に含まれているが、品質チェックの詳細実装は別モジュールに依存。
- ニュースの銘柄抽出は簡易的な 4 桁数字マッチに基づくため、将来的に NLP 等による精度向上が見込まれる。

---

Readers: 変更点はコードの実装内容から推測して記載しています。実際のリリースノートや日付は運用の都合に合わせて調整してください。