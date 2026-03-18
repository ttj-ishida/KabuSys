CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて調整してください。

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- 初期リリース: 日本株自動売買システム "KabuSys" の基本モジュール群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョン (0.1.0) と公開サブパッケージを定義。

  - 設定・環境変数管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
      - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD 非依存）。
      - 読み込み順序: OS環境変数 > .env.local > .env。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
      - .env の行パーサ（export KEY=val、引用符付き値、インラインコメント処理など）を実装。
      - .env.local は override=True（ただし OS 環境変数は保護）として読み込まれる。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（必須項目は未設定時に ValueError を送出）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須項目。
      - KABUSYS_ENV（development / paper_trading / live のみ許容）、LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
      - DB パス（DUCKDB_PATH, SQLITE_PATH）の Path 型返却、および is_live / is_paper / is_dev の便宜プロパティ。

  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
    - レート制限保護: 120 req/min を満たす固定間隔の RateLimiter を実装。
    - 再試行ロジック: 指数バックオフ（最大 3 回）を備え、408/429/5xx をリトライ対象にする。
      - 429 の場合は Retry-After ヘッダを尊重。
    - 認証トークン処理:
      - refresh token から id_token を取得する get_id_token() を実装（POST）。
      - 401 受信時は id_token を自動リフレッシュして一度だけ再試行するロジックを導入して無限再帰を回避。
      - モジュールレベルの id_token キャッシュを用いてページネーション間で共有。
    - ページネーション対応: fetch_* 関数は pagination_key を使って全件取得。
    - DuckDB への保存関数 save_* は冪等性を確保（INSERT ... ON CONFLICT DO UPDATE）し、fetched_at を UTC で記録して Look‑ahead bias を防止。
    - 型変換ユーティリティ (_to_float, _to_int) を実装（空値や不正フォーマットは None を返す、int 変換は小数切捨て防止ロジックあり）。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィードから記事を収集し raw_news / news_symbols に保存するワークフローを実装。
    - 設計上の主な特徴:
      - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。utm_* 等のトラッキングパラメータを除去して正規化。
      - defusedxml を使って XML Bomb などの攻撃に対策。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト検証、プライベート IP 判定による拒否（DNS 解決して A/AAAA を検査）。リダイレクト検査用のカスタムハンドラを実装。
      - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
      - HTTP レスポンスの Content-Length を事前チェックし大きすぎるレスポンスはスキップ。
      - テキスト前処理（URL 除去、空白正規化）を実施。
      - raw_news への保存はチャンク化してトランザクション内で行い、INSERT ... ON CONFLICT DO NOTHING RETURNING id により実際に挿入された記事IDのリストを返す。
      - 銘柄コード抽出ユーティリティ: 4桁数字パターンを検出し、known_codes セットでフィルタして重複排除したリストを返す。
      - run_news_collection() により複数ソースを安全に並列処理（ソース失敗時も他ソース継続）し、収集と銘柄紐付けを実行。

  - DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
    - Raw / Processed / Feature / Execution の多層スキーマを定義。
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切なデータ型・制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
    - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - init_schema(db_path) でディレクトリ自動作成（":memory:" をサポート）および DDL/インデックスを冪等に作成。
    - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分更新を主体とした ETL 実装（差分取得、保存、品質チェックフックを想定）。
    - ETLResult データクラスを導入し、取得／保存件数、品質問題、エラー概要を集約。品質問題は辞書化して出力可能。
    - 市場カレンダーを用いた取引日の調整ヘルパー（_adjust_to_trading_day）。
    - テーブル存在チェックや最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - run_prices_etl()（差分株価 ETL）の骨組みを実装:
      - デフォルトで最終取得日から backfill_days（デフォルト 3 日）をさかのぼって再取得し、API の後出し修正を吸収する設計。
      - 最低限取得開始日（_MIN_DATA_DATE = 2017-01-01）を定義。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- ニュース収集周りに複数のセキュリティ対策を実装:
  - defusedxml の採用（XML 脆弱性対策）。
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト先検査）。
  - レスポンスサイズ上限と gzip 解凍後の再チェック（DoS / decompression bomb 対策）。
- API クライアント側でもタイムアウト、再試行、レート制御を実装して外部 API に対する堅牢性を強化。

Notes / Implementation details
- 多くの保存処理は DuckDB の SQL を直接実行しており、パラメータ化クエリ・チャンク化・トランザクションを適切に利用することでパフォーマンスと一貫性を確保している（例: save_raw_news, _save_news_symbols_bulk）。
- 日付/時刻の扱い:
  - ニュース記事の pubDate は UTC に正規化して保存（naive datetime として扱うが UTC ベースで算出）。
  - fetched_at は UTC タイムスタンプ（ISO 8601、Z）で記録。
- 設定周りは OS 環境変数を最優先にするため、ローカルの .env による誤上書きを防ぐ仕組みがある（protected set）。
- 一部ユーティリティ関数はテスト容易性を考慮して差し替え可能（例: news_collector._urlopen をモックすることで HTTP 周りのテストが可能）。

今後の想定タスク（参考）
- run_prices_etl の続き（現在のコードは fetched 件数を返す処理が未完に見える箇所があるため最終戻り値の整備）。
- 品質チェックモジュール（quality）の実実装と ETL との統合。
- strategy / execution / monitoring サブパッケージの具体実装（プレースホルダ __init__.py が存在）。
- 単体テスト、統合テスト、CI 設定、ドキュメント整備。

--- 

この CHANGELOG はコード内容（関数名・ドキュメント文字列・設計コメント等）から推測して作成しています。実際の変更履歴・リリースノートを作成する際はコミットログやリリース方針に合わせて修正してください。