CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-18
------------------

追加 (Added)
- パッケージ初期リリース。日本株自動売買システム「KabuSys」の基礎モジュールを実装しました。
- パッケージメタ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポートモジュール: data, strategy, execution, monitoring
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート (.git または pyproject.toml を基準) から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env の行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、インラインコメントに対応）。
  - 環境設定 Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル検証など）。
  - DUCKDB / SQLite のデフォルトパス設定と Path での展開。
  - KABUSYS_ENV / LOG_LEVEL の入力値検証。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制限制御（固定間隔スロットリング）: 120 req/min を守る RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組み。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - 取得時刻を UTC で記録（fetched_at）し、Look-ahead バイアス対策を考慮。
  - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ (_to_float, _to_int) を提供（安全に None を返す）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得から raw_news への保存までのワークフローを実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
  - セキュリティ・堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス判定、リダイレクト先検査（カスタム RedirectHandler）。
    - レスポンス上限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS / Gzip bomb 対策。
    - 受信時の Content-Length チェックと実際の読み取りサイズの検証。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保（utm_* 等のトラッキングパラメータを除去して正規化）。
  - URL 正規化機能（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存はチャンク化・トランザクション化して効率化し、INSERT ... RETURNING を用いて実際に挿入されたレコードを返す:
    - save_raw_news（チャンク挿入、ON CONFLICT DO NOTHING、新規 ID を返却）
    - save_news_symbols / _save_news_symbols_bulk（ニュースと銘柄の紐付け）
  - 銘柄コード抽出: 正規表現による 4桁数字抽出と known_codes によるフィルタリング。
  - run_news_collection: 複数ソースを順次取得し、各ソースごとにエラーハンドリングして継続実行。新規挿入記事について銘柄紐付けを一括保存。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（型チェック、NOT NULL、CHECK 条件、外部キー）の定義。
  - 頻出クエリ向けのインデックス定義。
  - init_schema(db_path) によるディレクトリ作成＋DDL 実行での idempotent 初期化と get_connection を提供。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを実装（取得数、保存数、品質問題、エラー等の集約）。
  - 差分更新のためのユーティリティ: テーブル存在確認、最大日付取得、営業日に調整するヘルパー。
  - run_prices_etl 実装（差分更新ロジック、バックフィル、J-Quants 取得→保存の流れ。取得/保存カウントを返却）。
  - 設計方針に従い差分更新・backfill・品質チェック（quality モジュールとの連携設計）を想定した実装骨子。
- 空モジュール（プレースホルダ）:
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を追加（将来機能拡張用）。

セキュリティ (Security)
- RSS パーサで defusedxml を使用して XML に対する攻撃を軽減。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）。
- 外部 URL の受け入れは http/https のみ、mailto: 等は拒否。
- レスポンスサイズと gzip 解凍後サイズの上限チェックを実装し Gzip Bomb を防止。
- .env 読み込みに失敗した場合の警告や保護された環境変数を上書きしない仕組みを用意。

変更 (Changed)
- 初回リリースのため無し。

修正 (Fixed)
- 初回リリースのため無し。

注意事項・既知の制限 (Notes)
- jquants_client の設計は API レート・再試行・トークン更新を考慮していますが、運用環境でのログ出力やメトリクス収集（成功/失敗カウント）を追加することを推奨します。
- news_collector の _is_private_host は DNS 解決に失敗した場合は安全側で通す実装です（運用ポリシーにより挙動変更の検討可）。
- ETL の品質チェックモジュール (quality) は参照されているが、この差分からはその実装を含んでいません。品質判定の実装・ルール設定は別途必要です。
- pipeline.run_prices_etl 他の ETL ジョブ（財務データ・カレンダーの完全なスケジュール実行や統合結果出力）は今後の拡張対象です。
- strategy / execution / monitoring モジュールはプレースホルダとして用意されています。売買ロジック・発注連携は別実装。

互換性 (Compatibility)
- 初回リリースのため互換性の考慮は該当なし。

移行・アップグレード手順 (Migration)
- DuckDB スキーマは init_schema() が冪等にテーブルを作成するため、既存 DB があればスキーマ追加・変更時に init_schema を実行してマイグレーションを行ってください。外部キーやカラム追加に伴うデータ移行は別途検討が必要です。

お問い合わせ
- バグ報告や機能要望はリポジトリの Issue にお願いします。