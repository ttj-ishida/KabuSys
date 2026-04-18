# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

全般的な注意:
- 本リリースはパッケージ内のコア機能（設定管理、起動スクリプト、監視・実行エンジン起動補助、ポートフォリオ構築ユーティリティ、レポートツール、ユーティリティ群）の初期実装を含みます。
- 環境変数による設定・挙動上書きが多数用意されています。詳細は各モジュールの docstring / Settings を参照してください。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。
- 設定管理
  - Settings クラスを導入（src/kabusys/config.py）。
    - .env 自動ロード（プロジェクトルートの .env, .env.local）を実装。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 複雑な .env パース対応（`export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - 多数のプロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視しきい値 / 実行環境フラグ等）。
    - PAPER_FILL_MODE（`instant`/`partial`/`never`/`reject`）など Paper Trading 関連設定の検証。
- 設定支援 CLI
  - 対話式ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話式に行う。シークレット値はマスク表示。
    - 保存前に確認表示。
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証。
    - `--strict` オプションで警告も失敗扱いに可能。
- 起動スクリプト
  - 監視プロセス起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視は環境に依らず本番用の sqlite_path を使用する仕様。
    - monitoring DB 初期化（idempotent）と DuckDB 接続の確立。
  - 実行エンジン起動スクリプトを実装（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 DB（`paper_sqlite_path`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成。ExecutionEngine をスレッドで実行し、停止フラグを検知すると安全に停止。
    - 実行時に `data/execution.pid` 等の PID 管理ファイルを扱う。
    - RiskManager, OrderManager, Reconciler 等の組み立てとデフォルトパラメータを提供。
- ロギング & プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 引数や環境変数（LOG_LEVEL / LOG_DIR）で上書き可能。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度設定（high/normal/low）を提供。CPU affinity 設定機能も実装（第一 N コアにピン留め）。
    - 権限不足や未対応 OS の場合は警告を出してフェイルセーフ。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）。
  - セクターキャップ・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（売却予定銘柄を除外して既存エクスポージャーを算出、"unknown" セクターは制約除外）、calc_regime_multiplier（bull/neutral/bear のマッピング、未知値は警告して 1.0 フォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の割当ロジック、1 銘柄上限・aggregate cap、lot_size 単位丸め、cost_buffer（手数料・スリッページ見積）考慮。
  - これらをまとめたパッケージエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - CLI オプション `--from/--to/--db` をサポート。デフォルト DB は `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
- 研究用ファクター計算の下地
  - factor_research モジュールの導入開始（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR / 流動性等の計算方針と定数を定義。calc_momentum の実装を含む（ファイル末尾が部分的に省略）。
- パッケージメタ
  - パッケージ初期バージョン設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

### Changed
- ログの標準出力先として stderr ではなく stdout を採用（logging_setup）。cron 等で stdout/stderr を統一リダイレクトする運用を想定。
- run_monitoring の挙動: MONITOR_POLL_INTERVAL に不正な値が与えられた場合、ValueError を避けるためデフォルトにフォールバックして警告する実装に変更。

### Fixed
- .env パースの改善（src/kabusys/config.py）
  - 引用符付き文字列内部のバックスラッシュエスケープの扱い、インラインコメントの無視などに対応し、より堅牢な読み込みを実現。
- process_priority の例外ハンドリング強化（権限不足・未実装 API に対して警告してスキップ）。

### Notes / Migration
- 監視プロセスは「監視 DB」として Settings.sqlite_path を常に使用します（run_monitoring）。Paper Trading と分離したい場合は実行スクリプトを調整してください。
- Paper Trading 実行は Settings.is_paper に応じて `paper_sqlite_path` を使用します。Paper Trading 用 DB はデフォルトで data/paper_trading.db に保存されます。
- .env を新規作成する場合は `python -m kabusys.config_setup` を実行し、設定確認後に `python -m kabusys.validate_config` で検証してください。
- 既存運用でログディレクトリに書き込み権限がない環境ではファイル出力は無効化され、コンソール（stdout）への出力のみになります。

### Security
- シークレット（J-Quants トークン・kabu API パスワード等）は .env に平文で保持されます。`.env` を絶対に Git 等にコミットしないでください（config_setup のヘッダにも注意書きを追加済み）。

----

今後の予定（想定）
- factor_research の完全実装（Value/Volatility/Liquidity 等）。
- テストカバレッジの充実（ユニット・統合）。
- 実行エンジンと監視のより詳細なメトリクス・アラート連携（LINE 通知等）。
- 銘柄別 lot_size のサポート（stocks マスタから取得する設計への拡張）。