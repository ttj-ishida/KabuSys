# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（src/ 以下）の現状から機能追加・動作仕様・改善点を推測してまとめたものです。

## [Unreleased]
- なし

## [0.1.0] - 初回リリース
リリース日: 不明

### Added
- 実行エントリ / 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する。
    - 停止フラグファイル (data/stop_requested.flag) と実行 pid ファイル (data/execution.pid) を利用した安全な停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様を明示。
    - 停止フラグ検知でループを終了する仕組みを実装。

- 設定・環境変数管理
  - config.py
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
    - .env 自動ロード機能（プロジェクトルート自動検出: .git / pyproject.toml を基準）を実装。環境変数優先、.env.local を .env より優先して読み込む。
    - .env パース・検証に関する堅牢化（PAPER_FILL_MODE の有効値チェック、ログレベル・KABUSYS_ENV の検証など）。
    - paper_trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）を追加。
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを実装（secret マスク表示、選択肢・デフォルト対応）。
    - 生成される .env のテンプレートを定義。
  - validate_config.py
    - 起動前に環境変数・config/*.yaml を検証する CLI を追加。
    - `--strict` オプションで警告をエラー扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存ポジションのセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知値は警告してフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジック（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に応じたスケーリング）、手数料・スリッページ考慮（cost_buffer）をサポート。
    - 価格欠損時のスキップやスケールダウン時の端数処理（残差順に lot を追加）といった堅牢化を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを実装。
    - stdout へ出力する StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続するフェイルセーフを導入。
  - utils/process_priority.py
    - OS（Windows / POSIX）差分を吸収するプロセス優先度設定ユーティリティを追加。
    - CPU affinity 設定関数 set_cpu_affinity を追加（指定が None の場合は何もしない）。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。閾値はソース内で定義（例: 稼働率 >= 99%）。
    - --from/--to/--db オプションをサポートし、デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- 研究用ファクター計算基盤（部分実装）
  - research/factor_research.py
    - モメンタム・ボラティリティ・バリュー・流動性などの計算方針を定義。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。
    - モメンタム計算のための定数（1M/3M/6M, MA200 など）を定義（実装途中のファイルあり）。

### Changed
- ログ出力の標準化
  - すべての起動スクリプトが setup_logging を使用して統一的なログ設定を行うように変更（Stream stdout + 日次ファイル）。
- 起動時のプロセス優先度
  - run_execution と run_monitoring の起動直後に set_process_priority("high") を呼び出すようにしてプロセス優先度を向上。

### Fixed / Robustness
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いの改善を行いより多様な .env 形式に対応。
- ログディレクトリ作成失敗時の挙動を改善（ファイルハンドラを作成できない場合でもコンソールログで継続）。
- process_priority のクロスプラットフォーム差分を安全に扱うため AttributeError/NotImplementedError/AccessDenied を捕捉して警告を出す実装を追加。
- run_monitoring の MONITOR_POLL_INTERVAL のパースで 0 以下や不正値を検出した際にデフォルトにフォールバックし、警告ログを出すように修正（time.sleep に渡す不正値回避）。

### Security / Safety notes
- validate_config の live 環境チェックで、KABUSYS_ENV=live 時に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険値に対する警告を行うようにした（本番運用時の注意喚起）。
- .env ファイル生成ウィザードではシークレット値をマスク表示し、.env を絶対に Git にコミットしない旨の注意を出力。

### Documentation / Developer notes
- パッケージメタ情報: __version__ = "0.1.0"
- モジュール内に多数の docstring / コメントを追加し設計意図や TODO（例: lot_size 銘柄別サポート、価格フォールバック）を明示。
- tools と CLI に利用方法を示すヘルプ/usage を追加。

### Potential breaking changes / 注意点
- run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（Settings.sqlite_path）を使用するため、開発環境で monitoring を実行する際は sqlite_path を明示的に変更するか注意が必要。
- デフォルトのログディレクトリや DB パスは相対パス（data/, logs/）を利用するため、実行環境のカレントディレクトリやプロジェクト配置によってはディレクトリ作成が発生する点に留意。

---

変更点はソースコードのコメント・実装から推測してまとめています。追加の項目（実際のリリース日、細かいバグ修正、既知の問題など）はリポジトリのコミット履歴や issue を参照して補完してください。