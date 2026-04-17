# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

### 追加
- プロジェクトを初期リリース（kabusys v0.1.0）。
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを実行し、data/stop_requested.flag による安全停止をサポート。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB (data/paper_trading.db をデフォルト) を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理を実装。
    - 起動前に PID ファイル（data/execution.pid）を扱う設定を追加。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。デフォルト 60 秒のポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（不正値はデフォルトへフォールバック）。
    - 監視は常に本番用 sqlite_path を使用する設計（環境に依存しない）。
    - data/stop_requested.flag による停止検出と graceful shutdown を実装。
- 設定 / 環境読み込み機能を追加
  - config.Settings クラスを追加。アプリケーション設定を環境変数から取得するプロパティ群を提供。
  - .env 自動読み込みを実装（プロジェクトルートを .git / pyproject.toml から検出）。優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD によって自動ロードを無効化可能。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理、保護されたキー（OS環境変数）の上書き制御。
  - 新しい設定項目を追加:
    - PAPER_FILL_MODE（paper trading の MockBrokerClient の fill_mode。instant/partial/never/reject を検証）
    - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB パス）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEM/DISK）など監視・運用用パラメータ
    - LOG_LEVEL / KABUSYS_ENV 検証（許容値チェック）
- DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブル存在の保証（冪等）を実施。
- ポートフォリオ構築ライブラリを追加（純粋関数群）
  - portfolio.portfolio_builder: BUY シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全0時のフォールバック挙動を明示。
  - portfolio.position_sizing: 各銘柄の発注株数計算（risk_based / equal / score）。単元株数（lot_size）による丸め、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ想定）対応、利用可能現金に合わせた再配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。unknown セクターの扱い、既存売却予定銘柄の除外等を考慮。
  - package export を用意（kabusys.portfolio.* を再エクスポート）。
- リサーチ / ファクター計算モジュールを追加（duckdb ベース）
  - research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials テーブルを参照して計算。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク付けユーティリティ。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを整備（zscore_normalize を data.stats から再エクスポート）。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99%、成功率 90% など）。コマンドライン引数 (--from/--to/--db) に対応。
- AI ニューススコアリング基礎実装
  - ai.news_nlp: raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルへ書き込む処理を実装。バッチ処理（最大20銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、リトライ（429/5xx/ネットワークの指数バックオフ）、レスポンス検証、スコアクリッピングなどの堅牢化を導入。
  - ニュースの対象ウィンドウ計算（JST→UTC 変換）ユーティリティを実装。
- ユーティリティ
  - utils.process_priority: プロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し、失敗時は警告を出してスキップするフェイルセーフを採用。
- その他
  - パッケージ初期化とバージョン定義（kabusys.__init__ に __version__ = "0.1.0"）。

### 変更
- なし（初回リリースのため）。

### 修正
- なし（初回リリースのため）。

### 既知の注意点 / 設計上の注記
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
- 設定検証が厳密（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）なため、デフォルトや .env の値が許容範囲外の場合は起動時に ValueError が発生します。
- news_nlp は外部 API（OpenAI）を利用するため API キー管理とレート制御に注意してください（api_key 引数または OPENAI_API_KEY 環境変数でキーを供給）。
- 一部関数はデータ欠損時に None を返す等、防御的な挙動を取ります（欠損データに対するフォールバックはログに注目してください）。
- duckdb/SQLite に依存するため、初回起動時に DB スキーマの初期化やテーブル存在確認を行ってください（init_monitoring_db を利用）。

---

今後のバージョンでは、テストカバレッジの追加、AIニュース処理の冗長時の部分リトライ戦略、銘柄ごとの lot_size 対応、より詳細な運用ドキュメント（Deployment / Runbook）を予定しています。