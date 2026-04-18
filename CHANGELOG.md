# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」準拠です。  

リリース日付はコミット時点の想定（2026-04-18）です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - プロジェクト構成・主要モジュールを追加。
- 設定管理
  - Settings クラスによる環境変数ベースの設定管理を追加（kabusys.config）。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパース機能を強化（クォート、エスケープ、コメント、export プレフィックス対応）。
  - 必須値取得用の _require ヘルパーを追加（未設定時は ValueError）。
  - 設定ウィザード CLI を追加（python -m kabusys.config_setup）。対話式で .env を生成・更新可能。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、パス、YAML 構成ファイル等のチェック、--strict モードをサポート。
- 実行 / 監視
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアントの生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動処理。
    - 停止フラグ（data/stop_requested.flag）による安全な停止対応、実行 PID ファイル管理。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境設定にかかわらず Settings.sqlite_path（本番 sqlite_path）を使用する旨の動作注記。
    - 停止フラグ検知によるループ終了、check_once() 実行中の例外ハンドリングを実装。
- ロギング / プロセス管理
  - 統一ロギング設定ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーへ設定。
    - ログディレクトリ自動作成を試み、失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を行う。
    - CPU affinity 固定機能 set_cpu_affinity() を提供。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（kabusys.portfolio.portfolio_builder）。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（kabusys.portfolio.risk_adjustment）。
    - unknown セクターはセクター上限の対象外。
    - レジーム → multiplier マップを実装（bull/neutral/bear）。
  - 株数決定（ポジションサイジング）: calc_position_sizes（kabusys.portfolio.position_sizing）。
    - risk_based / equal / score の allocation_method をサポート。
    - lot_size（単元）で丸め、aggregate cap（available_cash を超えた場合）のスケールダウンと残差分配ロジックを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もるオプションを提供。
- 研究用ファクター計算（骨子）
  - DuckDB を使ったファクター計算モジュールの骨子を追加（kabusys.research.factor_research）。
    - モメンタム、ボラティリティ、バリュー等の定義と計算範囲定義（関数 calc_momentum 等の実装開始）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定する。
    - --from / --to / --db オプションをサポート。
    - デフォルト DB パスは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。

### Changed
- （この初版リリースにおいては既存の API 変更履歴は無し。全て新規追加。）

### Fixed
- 設定パーサーの堅牢化により、.env のクォート中のバックスラッシュエスケープや行内コメント処理の不整合を回避。
- logging_setup: ログディレクトリ作成に失敗した場合でもコンソール出力のみで起動を継続するよう改善。
- process_priority: 未対応 OS や権限不足時に例外を上げず警告でスキップするよう改善。
- run_monitoring: MONITOR_POLL_INTERVAL が不正な値（数値以外・0 以下）の場合にデフォルトにフォールバックする安全処理を追加。

### Notes / Important Behaviour
- 監視コンポーネント（run_monitoring）は「環境（KABUSYS_ENV）」にかかわらず Settings.sqlite_path を使用する設計です。テスト用に監視 DB を分離したい場合は sqlite_path を適切に設定してください。
- ExecutionEngine は paper_trading 環境時に paper_trading 用 SQLite を用いることで発注履歴が本番 DB と完全に分離されます。
- .env ファイルはセキュリティ上 Git にコミットしないでください（config_setup のヘッダーで注意書きを出力）。
- Settings の一部プロパティは入力検証を行い、無効値は ValueError を発生させます（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。

### Removed
- （該当なし）

### Security
- 秘密情報の扱い
  - config_setup の出力ではシークレット項目（トークン・パスワード）をマスク表示。
  - ただし .env の保存は平文のため取り扱いに注意。

---

参照:
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ユーティリティ: src/kabusys/utils/*
- ポートフォリオ: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py

（以上）