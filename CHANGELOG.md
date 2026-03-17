CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を想定しています。

[Unreleased]
------------

（現在のコードベースは初期リリース相当の実装を含むため、未公開の変更はありません）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ基盤
  - kabusys パッケージを追加。エクスポートモジュール: data, strategy, execution, monitoring。
  - バージョン情報: 0.1.0。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から探索するため、CWD に依存しない。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用等に利用可能）。
  - .env パーサーの実装（_parse_env_line）
    - export KEY=val 形式の対応、クォート内のバックスラッシュエスケープ処理、インラインコメント取り扱いの考慮。
  - .env の読み込み時に既存 OS 環境変数を保護する protected オプションを実装（override フラグで上書き制御）。
  - Settings クラスを導入し、設定アクセスをプロパティ化:
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境（KABUSYS_ENV） / ログレベル等を安全に取得。
    - 必須環境変数未設定時は明示的な例外（ValueError）を発生させる _require を提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セット）を実装。is_live / is_paper / is_dev の便宜プロパティを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しの汎用ユーティリティを実装（_request）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけ再試行（無限再帰対策あり）。
    - JSON デコード失敗時の明示的エラー化。
  - 認証ヘルパー get_id_token を実装（POST /token/auth_refresh）。
  - データ取得関数を実装:
    - fetch_daily_quotes: 株価日足（ページネーション対応）。pagination_key を利用して継続取得。
    - fetch_financial_statements: 財務データ（四半期 BS/PL、ページネーション対応）。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
    - 取得時に fetched_at を付与する設計方針を保持（Look-ahead Bias のトレースに配慮）。
  - DuckDB への保存関数（冪等／ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes: raw_prices へ保存（PK: date, code）、PK 欠損行のスキップとログ出力。
    - save_financial_statements: raw_financials へ保存（PK: code, report_date, period_type）。
    - save_market_calendar: market_calendar へ保存（取引日 / 半日 / SQ 日 フラグ化）。
  - 型変換ユーティリティを提供:
    - _to_float / _to_int：空値や不正値を安全に None に変換。_to_int は "1.0" のような表現を考慮して float 経由で変換し、小数部が残る場合は None を返す。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得して DuckDB に保存する一連の実装を追加。
  - セキュリティ / 安全対策:
    - defusedxml を利用して XML Bomb 等を防御。
    - SSRF 対策:
      - リダイレクト時にスキームとホスト（プライベート/ループバック等）を検証する _SSRFBlockRedirectHandler を実装。
      - 開始 URL に対する事前のプライベートホスト検証。
    - URL スキームは http/https のみを許可。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入し、読み込みで超過した場合は破棄（Gzip 解凍後サイズ確認含む）。
    - User-Agent と gzip Accept-Encoding を設定して取得。
  - TLS/HTTP 取得ユーティリティ _urlopen を抽象化（テストで差し替え可能）。
  - コンテンツ処理:
    - URL 正規化（_normalize_url）: 小文字化、トラッキングパラメータ（utm_ など）除去、フラグメント削除、クエリパラメータソート。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - テキスト前処理（preprocess_text）: URL 除去、空白正規化。
    - pubDate の robust なパース（_parse_rss_datetime）、失敗時は現在時刻で代替。
  - DB 保存機能:
    - save_raw_news: INSERT ... RETURNING を使って新規挿入された記事ID を正確に返す（チャンク分割、1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING で冪等に保存（INSERT ... RETURNING で実挿入数を取得）。
  - 銘柄コード抽出:
    - extract_stock_codes: テキスト中から 4 桁数字の銘柄コード候補を抽出し、known_codes フィルタで有効コードのみ返す（順序保持・重複除去）。
  - 高レベル統合ジョブ:
    - fetch_rss: 単一 RSS ソースの安全な取得とパース。
    - run_news_collection: 複数ソースを順次取得して保存、各ソースは独立してエラーハンドリング。新規記事に対して銘柄紐付けをまとめて追加。

- データベーススキーマ/初期化 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の多層構造）。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw Layer。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed Layer。
    - features, ai_scores など Feature Layer。
    - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution Layer。
  - 各テーブルに適切な型チェック制約（CHECK, NOT NULL, PRIMARY KEY, FOREIGN KEY）を付与。
  - パフォーマンスを考慮した頻出クエリ用のインデックスを定義。
  - init_schema(db_path) 実装:
    - 指定パスの親ディレクトリがなければ自動作成。
    - すべての DDL とインデックスを冪等に実行して DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を導入し、ETL 実行結果、品質問題、エラーメッセージを構造化して返却可能に。
  - 差分更新のユーティリティ:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
    - _adjust_to_trading_day: 非営業日の調整ヘルパー（market_calendar を参照、最大 30 日遡り）。
  - run_prices_etl 実装（差分取得 / バックフィル対応）:
    - 最終取得日が存在する場合はデフォルトで backfill_days（既定 3 日）分を巻き戻して再取得し、API の後出し修正を吸収する設計。
    - jq.fetch_daily_quotes から取得 → jq.save_daily_quotes で冪等に保存。
  - ETL 全体の設計方針:
    - 差分更新（営業日単位）を基本とし、品質チェックは fail-fast にしない（全件収集して呼び出し側で判断）。

Security, reliability and testability improvements
- 各所でログ出力（logger）を追加し、失敗時の原因追跡を容易に。
- ネットワーク関連は最大リトライ、指数バックオフ、Retry-After ヘッダ尊重（429）を実装。
- テスト向けの差し替えポイントを用意（例: news_collector._urlopen をモック可能、jquants_client の id_token 注入）。
- DuckDB 側ではトランザクションと INSERT ... RETURNING を積極的に用いて実挿入数を正確に把握。

Notes / Known limitations
- strategy, execution, monitoring サブパッケージの実態はこのリリースでは薄め（__init__.py の存在は確認できるが詳細実装は未記載）。
- pipeline モジュールは prices の差分 ETL を実装しているが、財務・カレンダー・品質チェックを統合する上位実行フローの完成度は今後の拡張対象。
- 外部 API のレスポンス仕様変更や DuckDB のバージョン差異により一部 SQL/型の調整が必要になる可能性がある。

Deprecated
- なし

Removed
- なし

Fixed
- なし

その他
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートやバージョン履歴は、プロジェクトのリリース運用方針に合わせて補正してください。