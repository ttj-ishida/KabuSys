# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

※ 本 CHANGELOG は、コードベースから推測して作成した初期リリース向けのまとめです。

## [Unreleased]

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージ情報: kabusys v0.1.0。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。  
    - 読み込み優先順: OS 環境変数 > .env.local > .env。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - 高度な .env パーサを実装（export KEY=val、クォート（シングル/ダブル）、バックスラッシュエスケープ、行内コメント処理をサポート）。
  - Settings クラスを実装し、環境変数の取得・検証を提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）。  
    - is_live / is_paper / is_dev といった環境判定プロパティを提供。
    - デフォルトパス等（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）を提供。
- 対話式設定ウィザード
  - config_setup.py による .env 初期作成／更新ウィザードを追加。  
    - シークレット値のマスク表示、選択肢サポート、保存確認を実装。
    - .env の雛形を書き出す _write_env を提供（書き出し時に .env を Git にコミットしない旨の注意付き）。
- 設定検証 CLI
  - validate_config.py を追加。環境変数や config/*.yaml の存在・基本整合性をチェック。  
    - 必須環境変数の未設定はエラー扱い。warning を fail とする --strict オプションを追加。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START 設定など）を実装。
- 実行・監視スクリプト
  - run_execution.py を追加（ExecutionEngine 起動ラッパー）。  
    - 起動時にプロセス優先度を high に設定（utils.process_priority.set_process_priority を使用）。  
    - paper_trading 環境では paper 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。  
    - BrokerClientFactory を用いたブローカークライアント生成をサポート（paper_trading 時は MockBrokerClient 想定）。  
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine をスレッドで実行。  
    - data/stop_requested.flag による外部停止フラグ検出、停止時の安全シャットダウン処理を実装。PID ファイルパスの注入をサポート。
  - run_monitoring.py を追加（SystemMonitor のポーリングループ起動）。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告の上デフォルトへフォールバック。  
    - 監視は環境にかかわらず本番 sqlite_path を使用し監視テーブルを初期化（init_monitoring_db）。  
    - stop flag の検出、例外発生時のログ出力、DB 接続の適切なクローズを実装。
- 監視 DB / DuckDB 統合
  - init_monitoring_db 呼び出しで監視テーブルの冪等な初期化を行うように各起動スクリプトで保証。
  - DuckDB 接続を分析用に利用（duckdb_path を Settings で管理）。
- utils/process_priority
  - プロセス優先度設定ユーティリティを実装（Windows と POSIX の差分を吸収）。  
    - Windows: psutil の HIGH_PRIORITY_CLASS 等を使用（getattr でフォールバック）。  
    - POSIX: nice 値を調整（Linux/Mac/FreeBSD をサポート）。  
    - 権限不足や未対応 OS は警告でスキップ。  
  - set_cpu_affinity を追加（最初の N コアに固定、例外は警告でスキップ）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア合計が 0 の場合は等金額フォールバックと警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用（既存保有のセクターエクスポージャーに基づき新規候補を除外）。unknown セクターは上限非適用。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。  
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を提供。不明レジームは 1.0 にフォールバック（警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。  
      - risk_based: portfolio_value, risk_pct, stop_loss_pct からリスクベースで算出。  
      - equal/score: 重みと max_utilization を考慮して配分。  
      - lot_size（単元）で丸め、max_position_pct による per-stock 上限を適用。  
      - aggregate cap により総投下額が available_cash を超える場合にスケールダウンし、残余キャッシュで端数を lot 単位で再配分するアルゴリズムを実装。  
      - cost_buffer を手数料・スリッページの見積りとして考慮。
- リサーチ / ファクター計算
  - research/factor_research.py を追加（DuckDB を用いたファクター計算）。  
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。ウィンドウ不足時は None。  
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率等を計算（未完の SQL 部分は継続して拡張想定）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加。ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を抽出してレポートを生成。  
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）など。  
    - デフォルト基準値（しきい値）を定義し PASS/FAIL 判定を出力。DB が存在しない場合のエラーメッセージを提供。  
    - 日付フィルタ（--from/--to）と --db オプションをサポート。
- その他
  - 複数ファイルで duckdb / sqlite の利用を想定し接続とクローズの扱いを統一的に実装。
  - ログ出力（logging）を各 CLI エントリポイントで基本設定（INFO レベル）を行うように実装。

Changed
- none（初期リリースのため変更履歴はなし）

Fixed
- none（初期リリースのため修正履歴はなし）

Known issues / Notes
- position_sizing: lot_size を銘柄毎に持つ拡張（lot_map）や価格欠損時のフォールバック価格（前日終値や取得原価）に関する TODO が残っています。
- process_priority / set_cpu_affinity: 実行環境の権限によっては設定失敗（警告でスキップ）します。運用環境での権限設定を確認してください。
- factor_research.calc_volatility の SQL 部分は長めのクエリであり、将来的に追加テストや最適化が必要です。
- validate_config の YAML 検証は PyYAML に依存します。PyYAML がない環境では警告になり検証の一部がスキップされます。

---

参考: 主な環境変数・設定キー
- KABUSYS_ENV (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- MONITOR_POLL_INTERVAL, PAPER_FILL_MODE
- KILL_FLAG_CLEAR_ON_START

（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートは運用ルールに従って適宜補完してください。）