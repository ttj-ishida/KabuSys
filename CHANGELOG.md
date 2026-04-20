# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

注: 以下の変更点は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。システム全体の基本コンポーネント、CLI ツール、ユーティリティ、ポートフォリオ構成ロジック、および検証／設定ウィザードを追加。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys v0.1.0）。
  - DuckDB / SQLite を用いたデータアクセス基盤の導入（duckdb_path, sqlite_path を設定可能）。
- 起動スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。
    - BrokerClientFactory によるブローカークライアント生成、ExecutionEngine / OrderManager / RiskManager / Reconciler を組み立ててセッションをスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と実行用 pid ファイル管理を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計（monitoring 用 DB 初期化を実行）。
    - 停止フラグ検知による graceful shutdown。
- 設定・検証
  - config: 設定管理クラス Settings を追加。
    - .env 自動ロード（プロジェクトルート検出（.git または pyproject.toml）に基づく）、ロード順序は OS 環境 > .env.local > .env。
    - .env 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数の取得ユーティリティ（必須チェック _require 等）、各種設定プロパティ（JQUANTS、KABU、DB パス、監視閾値など）を実装。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を実装。
    - KABUSYS_ENV, LOG_LEVEL の妥当性検証を実装（development / paper_trading / live 等）。
  - config_setup: 対話式 .env 作成・更新ウィザードを追加。
    - .env 読み込み／書き込み、シークレット項目のマスク表示、保存前の確認を実装。
    - 書き出しテンプレートに注意書き（.env を Git にコミットしない等）を含む。
  - validate_config: 起動前に設定を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック（PyYAML がなければ警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ログ・プロセス管理ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）をルートロガーへ設定。
    - LOG_DIR / LOG_LEVEL の解決、ファイル出力失敗時のフォールバックをサポート。
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定（high/normal/low）を行う set_process_priority。
    - set_cpu_affinity によりカレントプロセスを先頭 N コアに固定する機能を提供（権限不足等は警告でスキップ）。
- ポートフォリオ構成
  - portfolio.portfolio_builder:
    - select_candidates: シグナルのスコア降順選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中に基づく候補除外。sell_codes（当日売却予定銘柄）を除外する等の挙動を提供。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を算出。未知レジームは 1.0 にフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を使った保守的コスト見積と残差処理（lot 単位で追加配分）を実装。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg / max / P95）を算出して標準出力で報告。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数で期間や DB を指定可能。
    - P95 計算、期間フィルタ（ISO8601 タイムスタンプ）をサポート。閾値に基づく PASS/FAIL 判定（稼働率、fill_rate、send_rate、P95 レイテンシ等）。
- 監視関連
  - monitoring 側の初期化（init_monitoring_db）呼び出しを各起動スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - run_monitoring のポーリングループにおける例外ハンドリング（check_once の例外を捕捉してログ出力後に次ポーリングへ継続）。
  - 停止フラグ（data/stop_requested.flag）検知による安全停止ロジックを実装（監視・実行ともに）。
- research
  - research.factor_research: ファクター計算モジュールの骨組みを追加（Momentum 等の計算方針、定数、calc_momentum スタブが存在。DuckDB 接続を前提に計算）。

### Changed
- （初回リリースのため明確な「変更」はなし。設計上の決定点を記載）
  - 環境変数ロードのポリシーを明確化: OS 環境変数を保護しつつ .env.local が .env を上書きする仕組み。
  - ログ出力は標準出力（stdout）を利用し、ファイル書き込みに失敗した場合もコンソールログで運用可能にしている。

### Fixed
- （初回リリースのため顕在的なバグ修正履歴はなし。例外処理とフォールバックを強化することで堅牢性を向上。）

### Security
- 機密トークン等（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env に保存する前提だが、config_setup の注意喚起で .env を絶対に Git にコミットしないよう明記。

---

今後のリリースに向けてのメモ（推奨）
- research.factor_research の実装完了（calc_momentum 等の SQL/ロジックを追加）。
- Unit テスト / CI の追加（環境変数依存コードの分離とモック化）。
- ブローカークライアントのインターフェイス / モックの拡充と統合テスト。
- 単体・統合での負荷試験および監視アラートの強化（LINE 通知の実運用確認）。
- ポートフォリオロジックの拡張: 銘柄別 lot_size サポート、価格フォールバック戦略など。

以上。