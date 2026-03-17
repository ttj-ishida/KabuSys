# Changelog

すべての重要な変更点を記録します。本リポジトリは Keep a Changelog の慣例に従って管理されています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージとサブモジュールのエクスポートを追加（data, strategy, execution, monitoring）。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み実装（OS環境変数を保護する protected 機構を導入、読み込み優先順位: OS > .env.local > .env）。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサ実装: コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト用）。
  - Settings クラス: 各種必須環境変数の取得プロパティを提供（J-Quants / kabuステーション / Slack 等）。
  - バリデーション: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性検査。
  - デフォルトパス: DUCKDB_PATH / SQLITE_PATH のデフォルトを設定。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装。JSON デコード検査と詳細なエラーハンドリングを含む。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を遵守。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理: リフレッシュトークンから id_token を取得する get_id_token()、キャッシュと自動リフレッシュ（401 を受けた場合に 1 回リフレッシュして再試行）。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar。いずれも冪等（ON CONFLICT DO UPDATE）で保存。
  - データ変換ユーティリティ: _to_float / _to_int（堅牢な変換ロジック）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS 取得 / パース機能を実装（デフォルトソースに Yahoo Finance の RSS を設定）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクト先ごとのスキーム/ホスト検査を行うカスタム RedirectHandler を実装。ホストがプライベート/ループバック/IP マルチキャストの場合は拒否。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、受信中・gzip 展開後ともに上限チェック。
  - コンテンツ前処理: URL 除去、空白正規化。
  - URL 正規化と記事ID生成: トラッキングパラメータ（utm_*, fbclid 等）を除去し、正規化した URL の SHA-256（先頭 32 文字）を記事IDとして使用し冪等性を確保。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を利用して実際に挿入された記事IDを返す（チャンク化して 1 トランザクションで処理）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク挿入（ON CONFLICT DO NOTHING、チャンク化、トランザクション）。
  - 銘柄抽出: テキストから 4 桁の銘柄コード候補を抽出し、既知コードセット (known_codes) でフィルタ。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform 構成に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 制約・チェック（CHECK, PRIMARY KEY, FOREIGN KEY）やインデックス定義を含む。
  - init_schema(db_path): DB の初期化・テーブル作成と接続を返す（冪等）。親ディレクトリの自動作成対応。
  - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラス: ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約できる型を追加。
  - 差分更新ヘルパー: テーブル存在確認、最大日付取得（_get_max_date）および get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
  - 市場カレンダー補助: 非営業日の場合に直近の営業日に調整する _adjust_to_trading_day を実装。
  - run_prices_etl: 株価差分 ETL の入口実装（差分計算、backfill_days デフォルト 3 日、J-Quants から取得して保存する流れ）。差分ロジックと最小データ開始日（2017-01-01）を考慮。

### Security
- NEWS / RSS 処理における複数のセキュリティ強化:
  - defusedxml を使用した XML パース。
  - SSRF 対策: リダイレクト時のスキーム/ホスト検査、事前ホストチェック、プライベート IP の拒否。
  - レスポンスサイズの上限チェック（受信時および gzip 解凍後）。
  - URL スキーム検証（http/https のみ）。
- 環境変数読み込み時の OS 環境変数保護（protected set）によりローカル .env による意図しない上書きを防止。

### Notes / Implementation details
- API レート制限は固定間隔スロットリングで実装（120 req/min）。
- J-Quants クライアントの再試行は最大 3 回、401 発生時はトークンをリフレッシュして 1 回だけ再試行する設計。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）にし、データ後出し修正に耐えられるようにしている。
- news_collector は記事保存時に INSERT ... RETURNING を利用して実際に挿入された行のみを返すため、既存記事を重複カウントしない。
- pipeline.run_prices_etl は差分更新ロジックの実装を含むが、将来的にカレンダー取得や品質チェックとの統合が想定されている（quality モジュール参照）。

### Removed / Deprecated
- （今回のリリースでは該当なし）

今後の予定（例）
- pipeline の統合ジョブ（calendar / financials / quality チェックの実行と監査ログ出力）の追加
- strategy / execution / monitoring の実装拡充（現在はパッケージのスケルトンのみ）
- 単体テスト・CI ワークフローの追加

お問い合わせ・問題報告は Issue を作成してください。