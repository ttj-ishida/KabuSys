CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期の変更履歴です。

フォーマット:
- 変更はカテゴリ別に分類されています（Added, Changed, Fixed, Security 等）。
- 各リリースにはバージョンと日付を付与しています。

[Unreleased]
-------------

（なし）

0.1.0 - 2026-03-18
------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定モジュールを追加（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により CWD 非依存での自動読み込みを実現
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサー: export プレフィックス、クォート、インラインコメント、エスケープを考慮
  - settings クラスを提供し、以下の必須設定をプロパティで公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development, paper_trading, live のみ許可）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可）
    - デフォルトのデータベースパス（DUCKDB_PATH, SQLITE_PATH）

- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を提供
  - ページネーション対応（pagination_key を利用）
  - レート制限実装: 固定間隔スロットリング（120 req/min）
  - リトライ実装: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx
  - 401 レスポンス時は自動でリフレッシュトークンを用いて 1 回再試行
  - get_id_token 関数でリフレッシュトークンから idToken を取得
  - DuckDB への保存関数 save_* を提供（raw_prices, raw_financials, market_calendar）
    - 冪等性を考慮して INSERT ... ON CONFLICT DO UPDATE を利用
    - PK 欠損行のスキップ、ログ出力

- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols に保存するフルパイプライン
  - defusedxml を用いた XML パース（XML Bomb 対策）
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にスキームとホストを検証するカスタムリダイレクトハンドラ
    - プライベート/ループバック/リンクローカル/マルチキャスト IP の拒否（DNS 解決で A/AAAA を検査）
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を保証
  - トラッキングパラメータ（utm_* 等）を削除する正規化処理を実装
  - テキスト前処理 (URL 除去・空白正規化) を実装
  - DB 保存はチャンク化して一括 INSERT、INSERT ... RETURNING により実際に挿入されたレコードを返す
  - 銘柄コード抽出機能を実装（4桁数字を抽出して known_codes と照合）
  - run_news_collection により複数ソースの収集→保存→銘柄紐付けを一括で実行

- DuckDB スキーマ定義と初期化モジュールを追加（kabusys.data.schema）
  - DataPlatform に基づく 3 層＋実行レイヤーのテーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル制約（CHECK, PRIMARY KEY, FOREIGN KEY）を充実させたスキーマ
  - よく使うクエリに対するインデックス定義を追加
  - init_schema(db_path) でディレクトリ自動作成と全 DDL の冪等実行を行い、接続を返す
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）

- ETL パイプライン基盤を追加（kabusys.data.pipeline）
  - 差分更新・バックフィル（デフォルト backfill_days = 3）を行う設計
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）
  - ETLResult データクラスを追加（品質問題・エラー収集、to_dict を提供）
  - DB の最終取得日取得ユーティリティ（get_last_price_date 等）を提供
  - run_prices_etl の骨格を追加（差分取得→保存のフロー、jq.fetch_daily_quotes/jq.save_daily_quotes を利用）
  - テスト容易性のため id_token 注入可能な設計

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- RSS パーサ／フェッチ周りに多数の安全対策を実装
  - defusedxml を用いた XML パース
  - SSRF 対策（スキーム検査、プライベートホスト拒否、リダイレクト時の検証）
  - レスポンスサイズの上限設定と gzip 解凍後の再チェック
- API クライアントでトークン自動リフレッシュ・限定回数リトライを実装し、不正な認証状態への対処を改善

Deprecations
- （初版のため該当なし）

Removed
- （初版のため該当なし）

注意・移行メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参考に .env を配置してください（自動ロードはプロジェクトルート検出に依存）
- DB 初期化:
  - 初回実行時は kabusys.data.schema.init_schema(db_path) を呼んでください。":memory:" を渡すことでインメモリ DB が使用できます。
- ETL:
  - run_prices_etl 等は既存データの最終取得日を参照して差分を自動算出します。バックフィル日数や date_from を調整可能です。
- ログレベル・環境:
  - KABUSYS_ENV と LOG_LEVEL は許可値が限定されています。不正値を与えると ValueError になります。

既知の制約／今後の改善候補（推測）
- 現在はレートリミットが固定（120 req/min）でハードコードされているため、構成可能にする改善が考えられます。
- quality モジュールの実装参照（品質チェックの詳細実装）がパッケージ内で必要（pipeline が参照）。
- strategy, execution, monitoring パッケージは __init__ が存在するのみで具体的な機能実装は今後の追加が想定される。

--- 

脚注:
- 本 CHANGELOG は提供されたコードから推測して作成したものであり、実際のリリース履歴や運用ルールと若干異なる場合があります。必要に応じて補正してください。