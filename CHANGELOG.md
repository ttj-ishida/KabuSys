CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。
このファイルはパッケージのコードベースから推測して作成した初版の変更履歴です。

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリース（パッケージバージョン: 0.1.0）
  - パッケージ構成:
    - kabusys (トップモジュール)
      - data: データ取得・保存・ETL 関連
      - strategy: 戦略関連のプレースホルダ（パッケージ化）
      - execution: 発注/実行関連のプレースホルダ（パッケージ化）
      - monitoring: 監視関連（エクスポート済み）
  - 環境設定モジュール (kabusys.config)
    - .env ファイルまたは環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサ実装:
      - export プレフィックス対応
      - シングル/ダブルクォート内のバックスラッシュエスケープに対応
      - インラインコメントの処理（クォート有無で異なる扱い）
    - 環境変数アクセス用 Settings クラスを提供（必須値チェック、既定値、バリデーション）
      - 必須項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DB パスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/...）
      - ヘルパープロパティ: is_live / is_paper / is_dev
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API 呼び出しユーティリティ:
      - レート制限: 120 req/min 固定スロットリングを実装（RateLimiter）
      - リトライ: 指数バックオフによる最大 3 回の再試行（408/429/5xx 等を対象）
      - 401 の場合は自動でリフレッシュして 1 回リトライ（無限再帰を防止）
      - ID トークンのモジュールレベルキャッシュ（ページネーション間のトークン共有）
      - ページネーション対応のデータ取得関数:
        - fetch_daily_quotes（株価日足）
        - fetch_financial_statements（四半期財務）
        - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等設計: ON CONFLICT DO UPDATE）
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - データの取得時刻を UTC の fetched_at で記録（Look-ahead Bias 対策）
    - 値変換ユーティリティ: _to_float / _to_int（安全な変換・不正値は None）
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS 収集機能:
      - RSS の取得・XML パース（defusedxml を利用して XML Bomb 等に対処）
      - gzip 圧縮対応
      - レスポンスサイズ上限: 10 MB（超過時は安全にスキップ）
      - URL の正規化とトラッキングパラメータ除去（utm_* 等）
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証
      - SSRF 対策:
        - HTTP リダイレクト先を事前検査するカスタムハンドラ
        - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否
        - URL スキームは http/https のみ許可
      - テキスト前処理（URL 除去・空白正規化）
      - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）
    - DB 保存機能（DuckDB）:
      - save_raw_news: INSERT ... RETURNING を使い、実際に挿入された記事 ID を返却
      - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをチャンク挿入で保存（ON CONFLICT DO NOTHING）
      - トランザクションでまとめて処理し、失敗時はロールバック
  - DuckDB スキーマ定義 (kabusys.data.schema)
    - DataPlatform の 3 層構造に対応するテーブル群を定義:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 制約・CHECK・PRIMARY KEY を適切に付与
    - 頻出クエリ向けのインデックス定義
    - init_schema(db_path): 親ディレクトリを自動作成して全DDL・インデックスを実行（冪等）
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult dataclass で ETL 実行結果を集約（品質問題・エラー一覧・統計）
    - テーブル存在チェックや最終取得日取得のユーティリティ
    - 市場カレンダ補正関数 (_adjust_to_trading_day)
    - 差分更新ロジックの方針:
      - 最終取得日から backfill_days 分の再取得で API 後出し修正を吸収
      - デフォルトの backfill_days は 3 日
    - run_prices_etl: 差分取得→保存を行う個別 ETL ジョブ（fetch/save を呼び出す）

Security
- セキュリティ強化/防御実装
  - RSS/XML 処理で defusedxml を使用し XML 関連攻撃を軽減
  - RSS フェッチで SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - レスポンス読み取りサイズ上限を設けることでメモリ DoS を防止
  - .env 読み込み時に OS 環境変数を保護する機構（protected set）を導入

Changed
- （初版のため履歴上の「変更」はありません）

Fixed
- （初版のため履歴上の「修正」はありません）

Known issues / 注意点
- run_prices_etl の戻り値に関する実装の不整合（コードの途中で終端している様子）
  - run_prices_etl の末尾が "return len(records)," のように終わっており、期待される (fetched, saved) のタプルが正しく返されない可能性があります。実運用前に戻り値の整合性を確認・修正してください。
- 必須環境変数が未設定だと Settings._require により ValueError を送出するため、導入時は .env（.env.local）または OS 環境に必要変数を設定してください。
- DuckDB スキーマの作成は init_schema を明示的に呼ぶ必要あり。get_connection はスキーマ初期化を行いません。

Migration notes / 初期セットアップ
- .env.example を参考にして .env を作成し、以下の必須項目を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB をファイル保存する場合は init_schema(settings.duckdb_path) を一度実行してスキーマを作成してください（parent ディレクトリは自動作成されます）。
- 自動 .env 読み込みが不要なテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Authors
- コードベースより推測して作成された CHANGELOG（実際の authors 情報はリポジトリを参照してください）。

以上