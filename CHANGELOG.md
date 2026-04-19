# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
各リリースには主な追加・変更点を日本語で記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
最初の公開リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、設定管理、ポートフォリオ構築、検証ツール群を含む初期実装。

### Added
- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
    - プロセス優先度を開始時に High に設定。
    - duckdb を用いた接続を確立し、監視 DB 初期化を行う（init_monitoring_db 呼び出し）。
    - check_once() 実行中の例外は catch してログに残し、次のポーリングへ継続。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（実運用/モックを切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行し、停止フラグで安全に停止（_EXECUTION_PID ファイル指定機能あり）。
    - RiskManager の初期設定（max_position_pct, max_utilization 等）を実装、初期ポートフォリオ値は broker.get_available_cash() を用いる。

- 設定管理
  - src/kabusys/config.py
    - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env の読み込みは OS 環境変数を優先し、.env.local による override をサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
    - 複雑な .env 行のパースを実装（export プレフィクス、クォート文字列、エスケープ、インラインコメントの扱い）。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、DB パス、PID/kill flag パス、しきい値、環境種別、paper_trading 用設定など）をプロパティとして提供。
    - パラメータ検証を実装（KABUSYS_ENV / LOG_LEVEL の許容値チェック、PAPER_FILL_MODE の有効値チェックなど）。
    - settings = Settings() をモジュールレベルで提供。

  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。
    - J-Quants、kabu ステーション、ログ設定、DB パス、Kill Switch 設定などの主要項目を対話的に編集可能。
    - 既存 .env の読み込み/マスク表示、保存前の確認、ファイル書き出しロジックを提供。

  - src/kabusys/validate_config.py
    - 起動前に環境変数・config/*.yaml の妥当性を検証する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば実行）を行う。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を警告。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテート (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

  - src/kabusys/utils/process_priority.py
    - プラットフォーム差異（Windows / POSIX）を吸収したプロセス優先度設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を実装。
    - 権限不足などで設定できない場合は警告ログを出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
    - スコアが全て 0 の場合は等金額にフォールバックし警告ログを出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存保有と当日売却候補を考慮して候補をフィルタ）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear）。未知レジームは 1.0 でフォールバックし警告を出す。

  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジックを追加（allocation_method: "risk_based" | "equal" | "score" をサポート）。
    - リスクベース算出、単元株調整（lot_size）、1銘柄上限・aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer によるコスト見積もりを実装。
    - スケールダウン後の分配で端数（lot 単位）を残差に基づいて追加配分するアルゴリズムを実装。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をパッケージ公開用にまとめたエクスポートを提供。

- 研究 / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200 乖離、ATR、出来高等の計算を想定）。
    - 設計方針と定数が定義され、calc_momentum の実装を開始（ファイル末尾で途中まで記述）。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等の指標を DB（paper_trading.db）から集計して表示し、閾値比較で PASS/FAIL 判定を行う。
    - 閾値定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms など）をデフォルトで提供。
    - 日付フィルタ、DB パス指定オプションをサポート。

- パッケージ情報
  - src/kabusys/__init__.py
    - パッケージバージョンを __version__ = "0.1.0" として設定。
    - __all__ に主要サブパッケージを列挙。

### Changed
- （初期リリースのため該当なし）

### Fixed
- 設定・運用上の堅牢性向上
  - .env パーサは引用符・エスケープ・インラインコメントの扱いを適切に処理するように実装し、誤った行を無視することで読み込みエラーを回避。
  - MONITOR_POLL_INTERVAL が不正な値（0 以下や非数）の場合はデフォルト（60 秒）にフォールバックし、警告ログを出力する実装を追加。
  - logging_setup はログディレクトリ作成失敗時にファイルハンドラ追加をスキップし、代わりにコンソール出力へフォールバックするようにして起動失敗を回避。
  - process_priority 周りは権限不足や未対応 OS の場合に警告を出して安全にスキップするように実装。

### Known issues / TODO
- research/factor_research.py の calc_momentum 等、一部関数がファイル末尾で未完（実装途中）となっている箇所がある。今後のリリースで完了予定。
- position_sizing の価格欠損時の扱いに関する注記（price が欠損するとエクスポージャーが過少見積りされる可能性）が残されている。将来的に前日終値や取得原価などのフォールバックを導入予定。
- 単元株数 (lot_size) は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map の受け入れを検討。
- 本リリースでは一部の外部依存（psutil, duckdb, PyYAML など）を使用しており、環境によっては追加インストールが必要。

---

（この CHANGELOG はコードベースから推測して自動作成しています。実際のリリースノート作成時には追加の背景説明やマイグレーション手順を補完してください。）