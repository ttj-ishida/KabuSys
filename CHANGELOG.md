# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-18
初回リリース。パッケージ全体の初期実装を追加。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期モジュール構成を追加。
    - サブパッケージ: data, strategy, execution, monitoring（strategy / execution はプレースホルダ）。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードする機能を実装。  
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの柔軟なパース（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - OS 環境変数を保護する protected キーセットを導入（.env 上書き時に保護）。
  - Settings クラスを提供（プロパティを通じた設定取得、必須キーの検証）。
    - J-Quants / kabu API / Slack / DB パス / 環境 (development, paper_trading, live) / ログレベル の設定取得およびバリデーション。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装。
    - レート制限制御（固定間隔スロットリング: 120 req/min）。
    - リトライ（指数バックオフ、最大 3 回。対象: 408/429/5xx, ネットワークエラー）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とキャッシュ機構（モジュールレベル）。
    - ページネーション対応。
    - JSON デコードエラーのハンドリング。
  - データ取得関数を実装。
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
    - 全関数は id_token 注入可能でテスト容易性に配慮。
  - DuckDB への保存関数を実装（冪等性確保）。
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による重複排除／更新。
    - 各レコードに fetched_at を UTC（ISO）で付与し、データ取得時刻をトレース可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの収集処理を実装。
    - デフォルトソース: Yahoo Finance (news.yahoo.co.jp のビジネスカテゴリ RSS)。
    - URL 正規化（小文字化、トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb 等への防御）。
    - SSRF 対策:
      - リダイレクト先のスキーム＆ホスト検証を行うカスタム HTTPRedirectHandler を導入。
      - プライベート / ループバック / リンクローカル / マルチキャストのホスト/IP を検知して拒否。
      - http/https 以外のスキームを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存処理を実装。
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id を使用して新規挿入 ID を返す。チャンク & トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING + RETURNING を使用）。
  - 銘柄コード抽出ロジック（4桁数字候補と known_codes フィルタ）。
  - run_news_collection: 複数 RSS ソースから収集 -> raw_news 保存 -> 新規記事に対する銘柄紐付けを一括で実行。各ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含むテーブル定義を追加。
    - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各種制約・チェック（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - よく使われるクエリ向けのインデックスを作成。
  - init_schema(db_path) による初期化（親ディレクトリ作成、DDL 実行）と get_connection を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（取得数、保存数、品質問題、エラー等を保持）を追加。
  - テーブル最終日付取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 非営業日の調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl: 差分更新（最終取得日からの backfill を含む）で jquants_client 経由で取得・保存する処理を実装。
  - デフォルトのバックフィル日数やカレンダー先読み日数等の定数を定義。

### 変更
- （初版のため変更履歴なし）

### 修正
- （初版のため修正履歴なし）

### セキュリティ
- XML パースに defusedxml を使用し、XML-based attack を軽減。
- RSS フェッチに対して SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）を導入。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env による意図しない上書きを防止）。

### 注意事項 / 既知の問題
- src/kabusys/data/pipeline.py の末尾にある run_prices_etl の戻り値実装が途中で切れているように見えます（ファイル末尾が不完全）。実行時に Tuple の要件や saved 値の返却が期待通りでない可能性があります。CI/ユニットテストで確認・修正が必要です。
- strategy / execution サブパッケージは __init__.py が存在するのみで、実際の戦略ロジックや注文実行ロジックは未実装（プレースホルダ）。
- ニュース収集のデフォルト RSS ソースは限定的（現状は Yahoo Finance のみ）。追加ソースの設定・運用が必要。
- DuckDB スキーマは広範に定義されているが、アプリケーション層のマイグレーション/バージョニング戦略は未実装。

### マイグレーション / アップグレードノート
- 初回リリースのため移行手順はなし。DuckDB を利用する場合は init_schema() を用いて初期化してください。

---

今後のリリースでは以下を優先予定:
- pipeline の未完了箇所の修正（特に戻り値とエラー集約処理）。
- strategy / execution の実装（発注・約定処理、kabu API 実装）。
- 単体テスト・統合テストの追加（HTTP クライアントや DB 操作のモック導入）。
- 追加 RSS ソースやニュース分類（AI/センチメント）連携。