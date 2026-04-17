# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
重要: ここに記載した項目は、リポジトリの現在のコードベースから推測して作成した要約です（実装コメント・ドキュメント・コード構造に基づく）。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - DuckDB と SQLite を用いたローカルデータ基盤との連携を各種モジュールで実装。

- 実行／監視
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのエンジン実行および停止フラグ（data/stop_requested.flag）による制御を実装。  
    - エンジン用 PID ファイル出力サポート（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒、無効値時はフォールバック）。  
    - 監視は環境設定にかかわらず本番 sqlite_path を使用して監視テーブルを初期化・記録。

- 設定管理
  - config.Settings クラスを導入。環境変数から各種設定を取得するプロパティを提供（DB パス、API トークン、PID/kill フラグパス、監視閾値、PAPER_FILL_MODE 等）。  
  - .env/.env.local の自動読み込み機能を追加（OS 環境変数を保護する protected 仕組み、.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
  - .env パーサを強化（クォート処理、バックスラッシュエスケープの解釈、インラインコメント処理）。

- ポートフォリオ構築（portfolio）
  - portfolio_builder: BUY シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。  
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。  
    - セクター不明 ("unknown") の扱い、レジーム不明時のフォールバック、デバッグログを備える。
  - position_sizing: 株数計算ロジック（calc_position_sizes）を実装。  
    - allocation_method: "risk_based" / "equal" / "score" に対応。  
    - 単元株丸め（lot_size）、per-stock 上限・aggregate cap（available_cash）適用、cost_buffer による保守的見積り、縮小スケーリングと端数配分ロジックを実装。  
    - 価格欠損時のスキップ・デバッグログ。

- リサーチ（research）
  - factor_research: モメンタム（calc_momentum）、ボラティリティ・流動性（calc_volatility）、バリュー（calc_value）ファクター計算を実装。  
    - prices_daily / raw_financials テーブルを前提とした DuckDB ベースの SQL クエリ実装。欠損データ・行数判定により None を返す設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。  
    - 外部ライブラリに依存しない純粋な標準ライブラリ実装（pandas 不使用）。入力検証あり（horizons の整合性等）。

- AI / NLP（news_nlp）
  - ai/news_nlp.py: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し、銘柄ごとのスコアを ai_scores テーブルへ書き込む処理を実装（設計）。  
    - タイムウィンドウ計算（calc_news_window）、バッチ処理（最大20銘柄）、トークン肥大対策（記事数・文字数トリム）、リトライ（429/5xx/接続/タイムアウトに対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）等の仕様を実装。  
    - system prompt による厳密な JSON 出力指定。  
    - （注）score_news の実装はフェイルセーフ設計で API キー未設定時に例外を投げる等の検証を含む。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - CLI オプション (--from, --to, --db) をサポート。  
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を計算し PASS/FAIL 判定。  
    - データ不足やテーブル未存在時は N/A/0 を扱うフォールバックを持つ。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を提供（set_process_priority, set_cpu_affinity）。  
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した値をマッピング。psutil を用い、権限不足や未対応環境では警告を出して安全にフォールバック。

### 変更 (Changed)
- 設定のデフォルトとバリデーションを明確化（例: PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV / LOG_LEVEL の検証）。  
- DB 初期化処理（init_monitoring_db）が実行前提として各起動スクリプトで呼ばれるように変更（冪等に監視テーブルを保証）。

### 修正 (Fixed)
- .env パーサの改善により以下を正確に扱えるようにした:
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォートなし値におけるインラインコメントの判定（直前がスペース/タブ の場合のみコメントとみなす）
  - OS 環境変数の保護（.env.local による上書き時も保護キーは上書きされない）

### 注意点 / 既知の問題 (Notes / Known issues)
- ai/news_nlp.score_news の実装は途中（提示されたコードスニペットが途中で切れているため、実行時に未完成箇所がある可能性があります）。本機能は実験的であり、API コールの取り扱いや DB への部分的書き換えロジックに注意が必要です。  
- position_sizing / apply_sector_cap 内に将来的な拡張や TODO コメントあり（例: price 欠損時のフォールバック価格、銘柄ごとの lot_size をサポートする拡張）。  
- 一部の操作（プロセス優先度・CPU affinity 設定）は権限に依存し、環境によっては警告ログが出力されるが処理自体は続行される設計。

### セキュリティ (Security)
- 本リリースで特別なセキュリティ修正はありません。API キー等の取り扱いは環境変数経由で管理する設計。OpenAI API キー未設定時は明確なエラーを発生させる実装。

---

（今後のリリースでは、news_nlp の完全実装、単体テスト・統合テストの追加、lots/手数料モデルの拡張、より詳細な監視アラート・通知機能の追加を予定しています。）