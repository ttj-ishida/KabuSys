CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョン番号はパッケージ内の __version__（現状: 0.1.0）に対応します。

## [0.1.0] - 初回リリース

概要:
- KabuSys の初期実装をリリースしました。自動売買システム本体の起動スクリプト、設定管理、ロギング、プロセス優先度管理、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを含みます。

Added
- 基本 CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 SQLite（data/paper_trading.db, 環境変数で上書き可）を使用し、本番 DB と分離。
    - 停止制御に data/stop_requested.flag と data/execution.pid を使用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知、KeyboardInterrupt を考慮した安全なシャットダウン処理を実装。

- 設定・環境変数管理
  - config.py:
    - .env の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの取り扱い）。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、ログレベル、環境判定フラグ、Paper Trading 設定等）。
    - PAPER_FILL_MODE に対するバリデーション、有効値を限定。
  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新するツールを追加（.env を絶対にコミットしない旨の注意文書同梱）。
  - validate_config.py:
    - 起動前の設定検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML 未インストール時は警告）等を実施。
    - --strict オプションにより警告を失敗として扱える。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - stdout への StreamHandler と 日次ローテートする TimedRotatingFileHandler をルートロガーに設定するユーティリティを追加。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック（コンソール出力のみ）に対応。
    - 既存ハンドラを安全にクローズして再設定する実装。
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX 系）でプロセス優先度の設定を行う関数を追加（set_process_priority）。
    - CPU affinity を固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS の際は警告を出して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルの候補選択（select_candidates）、等金額配分（calc_equal_weights）、スコア比率配分（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター比率が上限を超える場合に新規候補を除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - 発注株数決定ロジックを実装（risk_based / equal / score の allocation_method、ロット丸め、1銘柄上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り）。
    - 単元株（lot_size）単位での丸めや残余配分ロジックを実装。

- 研究・解析補助
  - research/factor_research.py:
    - ファクター計算モジュール（モメンタム、MA200 乖離、ATR、流動性指標等）を開始。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（実装はモジュール内で進行中）。
  - DuckDB を分析 DB として扱う統合（duckdb_path 設定、複数モジュールで使用）。

- 運用ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite を解析して稼働率・注文成功率・送信率・レイテンシ（P95 など）をまとめるレポート生成 CLI。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）。
    - パス/値が不足する場合の N/A 表示や FAIL 判定ロジックを実装。

- 監視用 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して、起動時に監視用テーブルの存在を保証（冪等に実行）。

Changed
- ログ出力:
  - ログは標準出力 (stdout) を優先して出力するように設計（cron 等で stdout/stderr をまとめて扱う際の互換性向上）。
- .env 自動読み込みの挙動:
  - OS 環境変数を保護しつつ .env と .env.local を自動で読み込む挙動を導入。テスト時等に自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを追加。

Fixed / Improved
- 環境変数パースの堅牢化:
  - export プレフィックス・クォート・バックスラッシュ・インラインコメントなどに対応し、不正な行をスキップするロジックを導入。
- MONITOR_POLL_INTERVAL の検証:
  - run_monitoring のポーリング間隔環境変数は整数かつ正の値のみを許容し、不正値では警告を出してデフォルトにフォールバックするよう改善。
- DB ハンドリングの安全化:
  - 起動/終了時に SQLite / DuckDB コネクションを確実にクローズするように変更。
  - run_execution は paper_trading と本番 DB を環境に応じて明確に分離。
- エラーハンドリング:
  - monitor.check_once() 実行時の例外をキャッチしてログに残し、ポーリングループを継続するようにした（一時的な障害によりプロセスが落ちないように保護）。
  - process_priority や logging_setup での権限エラー / ファイル作成失敗時に警告を出してフォールバック。

Security
- .env の取り扱いに関する注意:
  - config_setup にて .env を生成するテンプレートを含め、ファイルを Git にコミットしないよう明示的な注意書きを追加。

Notes / Known limitations
- research/factor_research.py はファクター計算の設計を含むが一部実装が継続中（モジュール内に未完の箇所が存在）。
- position_sizing の価格取得失敗時（price が欠損・0）の扱いはログ出力に留めており、将来的にはフォールバック価格を導入する計画あり（TODO コメントあり）。
- process_priority / set_cpu_affinity は OS 権限やプラットフォーム依存のため、実行環境により期待どおり動作しない場合があります（警告ログでフォールバック）。
- validate_config による YAML 検証は PyYAML に依存。インストールされていない場合は内容検証をスキップして警告を出します。

導入方法・実行例（抜粋）
- .env の初期作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。今後のリリースでは、研究モジュールの完成、テスト追加、エラーハンドリングの拡張（リトライ/サーキットブレーカー挙動の統合）、および個別銘柄の lot_size マスタ対応などを予定しています。