# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。  
このファイルには主にコードベースから推測できる機能追加・動作仕様・既知の制約を記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys のコア機能群を実装。
  - portfolio モジュール（銘柄選定・重み計算・ポジションサイズ算出・リスク調整）
    - portfolio_builder:
      - select_candidates: スコア順に BUY 候補を選定
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算（スコアが全て 0 の場合は等分配にフォールバック）
    - position_sizing:
      - calc_position_sizes: risk_based / equal / score の各方式で銘柄ごとの発注株数を計算。単元株（lot_size）丸め、aggregate cap によるスケーリング処理を実装
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限チェックにより候補を除外（"unknown" セクターは上限対象外）
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数
  - research モジュール
    - factor_research: DuckDB 上の prices_daily/raw_financials を参照してモメンタム（1M/3M/6M、MA200乖離）やボラティリティ（ATR）、流動性指標を計算する関数群
  - 実行・監視用スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト（起動時にプロセス優先度を設定、DB 接続、ブローカーファクトリ、OrderManager/RiskManager/Reconciler を組み立ててエンジンを別スレッドで実行、停止フラグで安全にシャットダウン）
      - paper_trading 環境では MockBrokerClient と専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離
      - PID ファイル（data/execution.pid）管理、停止フラグ（data/stop_requested.flag）検出による起動抑止・シャットダウン
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可、デフォルト 60 秒）
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
  - 設定管理
    - config.py:
      - .env 自動読み込み（プロジェクトルートの .env/.env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
      - 環境変数用パースロジック (.env の引用、エスケープ、コメント対応)
      - Settings クラスによりアプリケーション設定をプロパティで提供（多くの既定値を含む）
      - PAPER_FILL_MODE の検証（有効値: "instant"|"partial"|"never"|"reject"）
    - config_setup.py: 対話式 .env 作成・更新ウィザード（既存値の再利用、シークレットのマスク表示、保存時の注意喚起）
    - validate_config.py: 起動前設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証、--strict オプションで警告もエラー扱い）
  - ユーティリティ
    - utils/process_priority.py:
      - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（psutil を利用）。権限不足等で失敗した場合は警告を出してスキップ
      - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を固定（サポート外 OS や権限不足時は警告）
  - ツール
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成ツール（期間指定可、P95 集計、稼働率・注文成功率・送信率・レイテンシの閾値判定を出力）
  - パッケージ情報
    - __version__ = "0.1.0"

### Changed
- （初回リリースのため履歴なし。設計上の既定値・挙動をドキュメントとして明記）
  - デフォルト設定・挙動の明記:
    - MONITOR_POLL_INTERVAL のデフォルト 60 秒（不正値は警告してデフォルトにフォールバック）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH のデフォルトパスを指定
    - ログレベル、KILL_FLAG_CLEAR_ON_START 等の環境変数による挙動制御

### Fixed
- （初回リリースに含まれる堅牢化）
  - .env パーサ: クォート内のバックスラッシュエスケープ・インラインコメント処理を実装し、より正確に環境変数を読み込めるように改善
  - DB 初期化: init_monitoring_db を起動時に冪等に呼び出して監視テーブルの存在を保証
  - Cross-platform: process_priority の実装で Windows/POSIX の差分に対応し、未対応 OS では安全にスキップ

### Notes / Known issues
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size を持たせる予定（現在は全銘柄共通の lot_size を想定）。TODO コメントあり。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされてセクター制限が適切に働かない可能性がある旨コメントあり。前日終値等を使うフォールバックは将来の拡張予定。
- Paper Trading の検証ツールは DB スキーマ（system_status, trade_logs, risk_logs 等）に依存する。スキーマが存在しない場合は N/A 表示や例外ハンドリングがあるが、完全互換性は要確認。
- run_monitoring は「監視は本番 sqlite_path を使用する」挙動のため、開発環境で誤って本番 DB を変更しないよう注意が必要。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」と明記（config_setup.py の出力ヘッダ）。
- Secrets（J-Quants トークン、kabuAPI パスワード、LINE トークン）は Settings 経由で必須/任意として扱い、validate_config で未設定警告を出す。

## References
- 実行例 / CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（必要に応じて今後のリリースで各モジュールの詳細変更点・バグ修正を追記してください。）