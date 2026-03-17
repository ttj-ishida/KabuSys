KEEP A CHANGELOG に準拠した変更履歴

すべての変更は SemVer に従います。  
このファイルはコードベース（version 0.1.0）から推測して作成したリリースノートです。

Unreleased
----------
- なし（初回リリースのため未発行）

[0.1.0] - 2026-03-17
-------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。公開モジュール: data, strategy, execution, monitoring（strategy/execution はプレースホルダとして存在）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 無効な行のスキップ。
  - Settings クラスで必須設定をラップ:
    - J-Quants / kabu API / Slack / DB パス等の取得プロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証。
    - duckdb/sqlite パスはデフォルトを持ち Path 型で返す。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得:
    - 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）。
    - ページネーション対応。ページネーションキーの重複防止ロジックあり。
  - 認証:
    - リフレッシュトークンからの id_token 取得（get_id_token）。
    - id_token のモジュールレベルキャッシュ実装（ページネーション間で共有）。
    - 401 受信時に自動でトークンを1回だけリフレッシュしてリトライするロジック。
  - レート制御とリトライ:
    - 固定間隔スロットリングで 120 req/min を順守する RateLimiter を実装。
    - ネットワーク/HTTP エラーに対する指数バックオフ付きリトライ（最大 3 回）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - 各保存処理は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複/再取得に耐性あり。
    - 保存時に fetched_at を UTC で記録し、データ取得時刻をトレース可能に。
  - データ型変換ユーティリティ:
    - _to_float, _to_int で安全に変換（空値/不正値は None、"1.0" のような表現の扱いにも注意）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS ベースのニュース収集機能を実装。
    - デフォルトソースに Yahoo Finance のカテゴリ RSS を設定。
    - fetch_rss により RSS を取得して記事リスト（id, datetime, source, title, content, url）を返す。
  - セキュリティ & 抵抗力:
    - defusedxml を使用した XML パースで XML Bomb 等を防止。
    - URL スキーム検証（http/https のみ許可）とホストのプライベートアドレス判定による SSRF 防御。
    - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ実装。
    - レスポンスの最大受信バイト数（10 MB）および gzip 解凍後サイズチェックを導入（メモリ DoS / Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）の除去、URL 正規化、SHA-256（先頭32文字）で記事 ID を生成して冪等性を確保。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用いて新規挿入された記事IDを正確に返す。チャンク（1000件）毎のバルク挿入、1 トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: ニュース記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING）し、挿入件数を正確に返す。
  - 銘柄コード抽出:
    - extract_stock_codes: テキストから 4 桁数字を抽出し、既知銘柄セット known_codes に基づき有効なコードのみを返す。
  - 統合収集ジョブ:
    - run_news_collection: 各ソース独立でエラーをハンドリングしつつ収集→保存→銘柄紐付けを行う。既知銘柄セットにより自動紐付けを実施。

- スキーマ & DB 初期化 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（CHECK, PRIMARY KEY, FOREIGN KEY）と検索や頻出クエリ用のインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成を行い、DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新中心の ETL 設計:
    - DB 側の最終取得日から差分を算出し、backfill_days により後出し修正を吸収して再取得。
    - 市場カレンダーは先読み（デフォルト 90 日）を想定。
  - ETLResult データクラスを導入し、フェッチ/保存件数、品質問題、エラー概要を集約。品質問題は quality.QualityIssue と整合。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - run_prices_etl（株価差分 ETL）の実装（date_from 自動算出、fetch→save の流れ）。

Security
- 環境変数の取り扱い、RSS の外部入力処理、HTTP リクエスト、XML パース等、複数箇所でセキュリティ対策を実施（SSRF, XML bomb, Gzip bomb, トラッキングパラメータの除去等）。

Notes / Known issues
- run_prices_etl の戻り値実装に不整合の可能性:
  - コード上の return 文が "return len(records), " のように末尾がカンマで終わっており、本来返すべき (fetched_count, saved_count) のタプルが正しく返されていない（saved 値が欠落している／実装不備）。挙動の確認と修正が必要。
- strategy と execution パッケージは __init__.py が空でプレースホルダとして存在するため、実戦運用用の戦略・実行ロジックは未実装。
- quality モジュールは pipeline で参照されるが、ここに含まれる品質チェックルールの実装状況に依存するため、実際の品質判定ポリシーは別途確認が必要。

Acknowledgements / Implementation details
- J-Quants クライアントは API レート制限（120 req/min）や 401 自動リフレッシュ、ページネーション共有用の id_token キャッシュを考慮して設計されています。
- DuckDB への保存は可逆的かつ冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING / RETURNING を多用）。
- RSS 処理では defusedxml, URL 正規化、トラッキング除去、プライベートアドレス検査などを組み合わせて堅牢化しています。

今後の改善候補
- run_prices_etl の戻り値修正と追加ユニットテストの整備。
- strategy / execution の実装およびエンドツーエンド統合テスト。
- quality モジュールの実装・設定と、ETL の品質チェックに基づく自動アラート/対応フロー。
- ロギングの構成（JSON ログ、外部監視連携等）やメトリクスの追加。
- Slack 通知連携や監視（monitoring モジュール）実装。

--- End of changelog ---