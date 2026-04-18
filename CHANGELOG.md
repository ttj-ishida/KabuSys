# チェンジログ

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルは、与えられたコードベースから推測して作成したものであり、実際のコミット履歴ではありません。

現在の日付: 2026-04-18

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回リリース（推測）。以下はコードベースから推測できる主な追加・実装内容です。

### 追加
- 全体
  - プロジェクト初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を併用するデータ基盤（設定可能なパス）を採用。
  - ログ出力を標準化するユーティリティを追加（TimedRotatingFileHandler を用いた日次ローテーション、コンソールは stdout に出力）。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モード判定を実装。paper_trading の場合は専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を結合して ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に関係なく本番用の sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt による終了をハンドリング。

- 設定関連
  - config.py: 環境変数と設定読み込み・ラッパーを追加。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env パースの堅牢化（export プレフィックス対応、シングル/ダブルクォート・エスケープ、インラインコメント扱いの分離）。
    - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DUCKDB/SQLite パス, paper_trading の設定, 監視閾値、ログレベル等）。
    - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）と便利プロパティ（is_live/is_paper/is_dev）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - よく使う項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話的に編集・保存。
    - 生成される .env に機密トークンはマスク表示で確認可能。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と (PyYAML があれば) パース検証、KABUSYS_ENV=live 時の追加警告を実装。
    - --strict オプションで警告をエラー扱いにして exit(1) を返す。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき候補を除外するロジック。既存ポジションのセクター別時価を計算し上限超過セクターの新規候補をブロック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
      - risk_based: 許容リスク率、損切り率等からベース株数を計算。
      - equal/score: 重みに基づきポジションを算出。単元株（lot_size、デフォルト 100）で丸め。
      - aggregate cap（available_cash）を越える場合はスケールダウンし、残余を fractional 残差の大きい順で lot_size 単位で再配分。
      - cost_buffer により手数料やスリッページを保守的に見積もる。

- ユーティリティ
  - utils.logging_setup: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度設定 API を追加（set_process_priority）。Windows/Linux（POSIX）差を吸収。CPU affinity を固定する set_cpu_affinity を提供（psutil ベース）。呼び出し側はプラットフォーム差を意識しなくて良い。
  - 停止および PID 管理のためのファイルパス（kill/stop/pid）を標準化して使用。

- ツール
  - tools.paper_verification_report: ペーパートレード用の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を計算してレポート化。
    - 判定閾値（稼働率、fill/send 率、P95 レイテンシ）を定義し PASS/FAIL を判定。
    - P95 計算実装（サンプル数が小さい場合を考慮）。
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。

- 研究用モジュール（research）
  - research.factor_research: ファクター計算モジュールを実装（Momentum, Value, Volatility, Liquidity 等の計算を想定）。DuckDB の prices_daily / raw_financials を参照する設計。モメンタム計算関数のスケルトン（calc_momentum）を実装（途中でファイルが切れているが、設計方針と定数は実装済み）。

### 変更
- 設定読み込みの優先度を明確化
  - OS 環境変数 > .env.local > .env の順で読み込む実装。.env.local は .env 上書き、ただし OS 環境変数は保護される（protected set）。
- ロギング
  - stdout に出力するよう統一（cron/Task Scheduler などでのリダイレクトを想定）。
  - 既存ハンドラがある場合は一度 flush/close してから再設定することで二重ログを防止。

### 修正（設計上の注意・フォールバック対応）
- 環境変数パースの堅牢化により、引用符付き値やバックスラッシュエスケープ、インラインコメント等が正しく扱われるように改善。
- score ベース配分で全スコアが 0 の場合は等金額配分にフォールバックして警告を出す（calc_score_weights）。
- ログディレクトリ作成やプロセス優先度設定が失敗した場合は警告を出して安全にスキップする実装（実行継続性を重視）。

### 既知の挙動・注意点（breaking-ish）
- 監視ランナー（run_monitoring）は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用する設計。開発/ペーパー環境で監視データを分離したい場合は注意が必要（意図的な設計の可能性あり）。
- calc_position_sizes の per-stock 上限計算では price が欠損（0.0）の場合、エクスポージャーや上限推定が過少になる可能性があり、将来的に価格フォールバック（前日終値や取得原価）を検討する旨の TODO がある。
- research.factor_research はファイル末尾で途中になっており、実装が未完と思われる（追加実装が必要）。

### ドキュメント・ユーザービリティ
- config_setup と validate_config により、導入時の .env 作成と起動前チェックが容易になっている。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途を想定）。

### セキュリティ
- シークレット項目（API トークン等）を対話ウィザードで入力する際はマスクして表示。  
- .env の自動生成コードに「.env は絶対に Git にコミットしないこと」と注意喚起あり。

---

（補足）実際のリリースノートやバージョニングはコミット履歴・問題トラッカー等に基づいて作成してください。本 CHANGELOG は提供されたソースコードの内容から推測した要約です。必要であれば、各項目をさらに分割して詳細な説明や影響範囲（例: どの CLI/スクリプトが影響を受けるか、具体的な環境変数名など）を追記します。