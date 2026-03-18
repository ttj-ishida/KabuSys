CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトの初期リリース v0.1.0 をコードベースから推測して作成しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルと OS 環境変数の自動読み込み機能を追加
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env 読み取り時の保護機構: OS 環境変数は protected として上書きを防止
  - 独自の .env パーサ実装
    - export KEY=val 形式、シングル・ダブルクォート、エスケープ、インラインコメントの扱いに対応
  - Settings クラスを提供（型付きプロパティ）
    - J-Quants / kabuステーション / Slack / DB パスなどの必須/既定値設定
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値チェック）
    - ユーティリティ: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装
    - ベース URL、ページネーション対応の fetch_* API（株価・財務・カレンダー）
    - レート制限: 固定間隔スロットリング（120 req/min）
    - 再試行ロジック: 指数バックオフ、最大 3 回（408/429/5xx をリトライ）
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時は自動でリフレッシュトークンを使って id_token を再取得し 1 回のみリトライ
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
  - データ取得関数
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - ページネーションキーの追跡による重複防止
    - 取得時ログ出力（取得件数）
  - DuckDB への冪等保存関数
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による上書きで冪等性を担保
    - PK 欠損行のスキップと警告ログ
    - レコード作成時に fetched_at（UTC）を記録
  - 値変換ユーティリティ
    - _to_float / _to_int（安全な変換、空値や不正値は None）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS からニュース記事を収集し raw_news, news_symbols に保存する実装
    - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）
    - RSS の取得、XML パース（defusedxml を利用）、記事抽出
    - テキスト前処理: URL 除去、空白正規化
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成（utm_* 等のトラッキング除去）
    - Gzip 圧縮対応と受信サイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）
    - SSRF 対策
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルか判定し拒否
      - リダイレクトを検査するカスタムハンドラ実装
    - DB 保存はチャンク化（_INSERT_CHUNK_SIZE）し、トランザクションでまとめて実行
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し新規挿入 ID を返却
      - save_news_symbols / _save_news_symbols_bulk: INSERT ... RETURNING で新規挿入数を正確に取得
    - 銘柄コード抽出
      - 正規表現で 4 桁数値を候補抽出し、known_codes に基づいてフィルタ
  - run_news_collection: 全ソースの収集を統括し、個別ソースの失敗は他ソースに影響を与えない設計

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各レイヤー向けテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各カラムに型と CHECK 制約を付与（例: side/check list、価格/サイズの非負チェックなど）
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) でディレクトリ作成・DDL 実行して接続を返す（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン基礎 (kabusys.data.pipeline)
  - ETL の設計に沿ったユーティリティ実装
    - ETLResult データクラス（処理結果/品質問題/エラー収集）
    - 差分更新ヘルパー: テーブル最終日取得、営業日調整
    - run_prices_etl（差分取得→保存の個別 ETL ジョブ）
      - 最終取得日から backfill_days（デフォルト 3 日）を用いた差分再取得ロジック
      - J-Quants の fetch/save を利用して取得・保存
  - テスト容易性を考慮した設計（id_token 注入可能、_urlopen モック等）

- パッケージ構造
  - data, strategy, execution, monitoring を __all__ で公開（strategy・execution の __init__ は現時点でプレースホルダ）

Security
- RSS パースに defusedxml を利用し XML 攻撃を軽減
- SSRF 対策を複数レイヤで実施（スキーム検査、プライベートホスト判定、リダイレクト時の再検査）
- ネットワーク受信サイズ制限（10MB）および gzip 解凍後の再検査でメモリ DoS を軽減

Notes / Known issues
- run_prices_etl: コード末尾で return 文が途中で終了している（len(records), のみで saved 値が返されていないように見える）。本番利用前に戻り値の修正が必要。
- strategy/ execution / monitoring パッケージは現時点では実装が見当たらずプレースホルダの状態。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされる（CI/配布後に注意）。
- jquants_client._request は最大リトライ失敗時に RuntimeError を送出する設計。呼び出し側でのエラーハンドリングが必要。
- ニュース収集の銘柄抽出は単純な 4 桁数列マッチであり、誤検出や文脈解釈が不要なケースは残る（known_codes によるフィルタで軽減）。

Migration / Upgrade notes
- DuckDB の初期化は init_schema() を呼ぶことで実行される。デフォルトのファイルパスは settings.duckdb_path（"data/kabusys.duckdb"）となる。
- 既存 DB に対しては init_schema が冪等にテーブル／インデックスを作成するため、安全に実行可能。

Contributors
- Initial implementation (コードベースから推測して記載)

References
- この CHANGELOG はリポジトリ内の src/kabusys 以下の実装に基づいて生成しています。