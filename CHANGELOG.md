Changelog
=========
すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-18
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの骨子を実装。
  - パッケージ構成
    - kabusys パッケージエントリを定義（__version__ = 0.1.0）。
    - public API: data, strategy, execution, monitoring をエクスポート。
  - 環境設定 (kabusys.config)
    - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルートは .git または pyproject.toml から探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env の行パーサ: export プレフィックス、クォート文字（エスケープ対応）、インラインコメントルール等をサポート。
    - Settings クラス: J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）の検証、LOG_LEVEL の検証、ユーティリティプロパティ（is_live／is_paper／is_dev）。
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API ベース URL, レート制限（120 req/min）を実装する固定間隔スロットリング（RateLimiter）。
    - HTTP リクエストユーティリティ: JSON デコード、タイムアウト、クエリパラメータ組立て。
    - 冪等かつページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足 / OHLCV）
      - fetch_financial_statements（四半期財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータスコード（408、429、および 5xx）をリトライ。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰を避ける設計）。
    - id_token のモジュールレベルキャッシュを持ち、ページネーション間で共有。
    - DuckDB へ保存する冪等化関数:
      - save_daily_quotes（raw_prices: ON CONFLICT DO UPDATE）
      - save_financial_statements（raw_financials: ON CONFLICT DO UPDATE）
      - save_market_calendar（market_calendar: ON CONFLICT DO UPDATE）
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。
    - 型変換ユーティリティ（_to_float / _to_int）: 空値や不正値を安全に扱う。
  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードから記事を収集し raw_news に保存する一連の機能を実装。
    - セキュリティ・堅牢性:
      - defusedxml を用いた XML パース（XML Bomb 等の防止）。
      - リダイレクト時にスキームとホストを事前検証するカスタムハンドラ（SSRF 対策）。
      - URL スキーム制限（http/https のみ）とプライベートアドレス拒否。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の検査（Gzip bomb 対策）。
      - 受信ヘッダの Content-Length を利用した事前チェック。
    - フィードパース・記事処理:
      - URL 正規化（小文字化、tracking パラメータ除去、フラグメント削除、クエリソート）。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
      - テキスト前処理（URL 除去、空白正規化）。
      - pubDate のパース（RFC 2822 準拠）と UTC での正規化（パース失敗時は現在時刻で代替）。
      - fetch_rss は名前空間付きフィードや非標準レイアウトにフォールバック。
    - DB 保存・紐付け:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用い、チャンクごとにトランザクションで実行。実際に挿入された記事 ID を返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク挿入で実装（ON CONFLICT DO NOTHING + RETURNING で正確な挿入数を返す）。
    - 銘柄コード抽出:
      - extract_stock_codes: 正規表現で 4 桁数字を候補抽出し、known_codes に存在するものだけを返す（重複除去）。
    - run_news_collection: 複数ソースを順次収集し、失敗したソースはスキップして他のソース収集を継続。既知銘柄との紐付けを一括で行う。
  - スキーマ定義 (kabusys.data.schema)
    - DuckDB 用のスキーマ（Raw / Processed / Feature / Execution 層）を DDL で定義。
    - 主要テーブル（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を含む。
    - 型・チェック制約（CHECK、NOT NULL、PRIMARY/FOREIGN KEY）を定義し、データ整合性を高める。
    - よく使うクエリ向けのインデックスを作成（code×date スキャン、status 検索など）。
    - init_schema(db_path) による冪等的な初期化（親ディレクトリ自動作成、:memory: サポート）。
    - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETL の設計方針（差分更新、backfill による後出し修正吸収、品質チェックは集約して報告）を実装。
    - ETLResult dataclass を追加（取得数・保存数・品質問題・エラー一覧を保持、has_errors / has_quality_errors 等の便利プロパティを提供）。
    - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists / _get_max_date）。
    - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）。
    - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl: 差分 ETL の実装（最終取得日に基づく date_from の自動算出、backfill_days のサポート、fetch -> save の流れ）。
  - その他
    - モジュール単位でのロギングを適切に出力し、処理状況や警告を追跡可能に。

Security
- ニュース収集での SSRF 対策、defusedxml による XML 安全化、レスポンスサイズ制限、URL スキーム制約を導入。
- 環境変数の取り扱いでは OS 環境変数を優先・保護することで意図しない上書きを防止。

Notes
- DuckDB スキーマは多数のテーブル・制約を含むため、既存 DB に適用する際はバックアップ推奨。
- J-Quants API の rate limit（120 req/min）を守る設計だが、運用時に他のコンポーネントと合わせた実行頻度の調整が必要。
- run_prices_etl 等はテスト容易性のため id_token を注入可能にしており、ユニットテストで外部 API 呼び出しをモック可能。

未解決 / 今後の課題（予定）
- strategy、execution、monitoring パッケージの実装拡張（現状はパッケージプレースホルダ）。
- quality モジュールの品質チェックルール拡張（現在は pipeline からの参照想定）。
- ETL のログ・監査強化（冪等性の追加検証や履歴管理）。

--- 

（注）この CHANGELOG は提供されたソースコードからの推測に基づいて作成した初期リリース記録です。実際のリリースノートとして用いる際は、リポジトリのコミット履歴や運用での決定事項に合わせて調整してください。