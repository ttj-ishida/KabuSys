Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。プロジェクトの現状（コードから推測）に基づき、実装された機能・設計方針・既知の問題点を記載しています。

CHANGELOG.md
============
すべての変更は "Keep a Changelog" に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
### 追加予定 / 既知の問題
- run_prices_etl の戻り値が不完全（現在の実装だとタプルの片側しか返していない可能性あり）。この点は次のリリースで修正予定。

0.1.0 - 2026-03-17
------------------
### 追加 (Added)
- 初期リリース: kabusys パッケージ（バージョン 0.1.0）
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）  
    - パブリックモジュール: data, strategy, execution, monitoring（現時点では一部がプレースホルダ）

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パースの堅牢化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートの中でのバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無での挙動差異）
  - 環境変数保護:
    - OS 環境変数を protected として .env による上書きを防止
  - Settings クラス:
    - 必須設定取得ヘルパー（_require）
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）
    - is_live / is_paper / is_dev 判定プロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 提供 API:
    - get_id_token (refresh)
    - fetch_daily_quotes（ページネーション対応）
    - fetch_financial_statements（ページネーション対応）
    - fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - 設計要点:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック:
      - 最大 3 回、指数バックオフ
      - 再試行対象: 408, 429, 5xx/ネットワークエラー
      - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限ループ防止）
    - モジュールレベルの id_token キャッシュを保持（ページネーション間共有）
    - 取得時刻（fetched_at）を UTC ISO 形式で保存（Look-ahead bias 防止のため）
    - DuckDB への挿入は ON CONFLICT DO UPDATE により冪等性を確保
    - JSON デコード失敗や HTTP エラー時の明確な例外ログ

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集 + DuckDB への保存機能
  - 機能:
    - fetch_rss: RSS 取得・XML解析・記事整形（タイトル/本文の前処理）
    - preprocess_text: URL 除去、空白正規化
    - URL 正規化: トラッキングパラメータ削除（utm_ 等）、フラグメント除去、クエリソート
    - 記事IDの生成: 正規化 URL の SHA-256 を用い先頭32文字を採用（冪等性）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストがプライベート/ループバック/リンクローカルでないことを検証（DNS 解決済み）
      - リダイレクト時に検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）
      - _urlopen をテスト用に差し替え可能に設計
    - 安全対策:
      - defusedxml を利用して XML Bomb 等を緩和
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後も検査（Gzip bomb 対策）
    - DB 操作:
      - save_raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用。1 トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付け保存（INSERT ... RETURNING を活用）、トランザクション管理
    - 銘柄抽出:
      - extract_stock_codes: 正規表現で 4 桁数字を抽出し、known_codes に基づきフィルタ・重複除去
    - run_news_collection: 複数ソースの収集をまとめて実行。ソース単位でエラーハンドリング（1 ソース失敗でも他は継続）

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - 3 層＋実行層に基づくテーブル定義を提供（Raw / Processed / Feature / Execution）
  - 代表的なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・インデックスを含む DDL を定義
  - init_schema(db_path): 親ディレクトリ自動作成、すべての DDL/インデックスを実行して DuckDB 接続を返す（冪等）
  - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（品質問題やエラーの集約）
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day: 非営業日調整（最大 30 日遡る）
  - run_prices_etl:
    - 差分更新ロジック（最後の取得日から backfill_days を考慮して date_from を自動計算）
    - 最小データ開始日を定義（2017-01-01）
    - jq.fetch_daily_quotes → jq.save_daily_quotes を呼び出すフロー
    - 品質チェック（quality モジュール）との統合を想定した設計（実装では quality モジュールとの連携ポイントあり）

### セキュリティ (Security)
- RSS XML のパースに defusedxml を利用（XML 関連攻撃対策）
- RSS フェッチにおける SSRF 対策:
  - スキーム検証（http/https のみ）
  - ホスト/IP のプライベートアドレス検出（DNS 解決結果含む）
  - リダイレクト時に都度検証するカスタムリダイレクトハンドラ
- .env の自動読み込みにおいて OS 環境変数を上書きしない既定挙動と、上書き時の保護処理を実装

### 変更点 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

重要な注意（Known issues / TODO）
- run_prices_etl の戻り値がコード末尾で不完全に見える（return len(records), のように保存件数を含めて返していない、あるいは誤ったタプル構成）。ETL の呼び出し元と結果利用時に影響するため、次回リリースで確認・修正を推奨。
- strategy, execution, monitoring モジュールはパッケージに含まれているが、現コードは __init__ による公開のみで実装が空または未提供（プレースホルダ）。

配布・導入メモ
- DuckDB を利用するため、環境に duckdb パッケージが必要。
- J-Quants / Slack / kabu API を利用する機能は環境変数に依存（.env/.env.local または OS 環境を設定）。
- 自動 .env ロードはプロジェクトルート検出に依存（.git または pyproject.toml）。配布後は自動ロードの挙動に注意。

貢献・追記
- 各モジュールはテスト容易性を考慮して依存注入やフック（例: _urlopen の差し替え, id_token の引数注入）を用意しています。ユニットテスト追加や品質チェック機能の実装・有効化を推奨します。

--- 
以上がコードベースから推測した CHANGELOG.md の内容です。必要であれば、日付・バージョンや「既知の問題」をさらに詳細化して更新します。