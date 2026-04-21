# Changelog

すべての重要な変更履歴を記録します。フォーマットは "Keep a Changelog" に従います。  
リリースはセマンティックバージョニングに準拠しています。

最新の変更は主に初回リリースとしてまとめています。

## [Unreleased]

- （今後の変更をここに記載）

## [0.1.0] - 2026-04-21

Added
- パッケージ初期リリース（__version__ = 0.1.0）。
- エントリスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御にプロジェクト直下の `data/stop_requested.flag` を利用。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様を採用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory を介して）を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 実行中は `data/execution.pid` に PID を書き、停止フラグを検知したら安全に停止。
    - プロセス優先度を "high" に設定。
- 設定/環境周り
  - config.py
    - 環境変数読み込み・管理クラス `Settings` を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 自動ロード機能を実装（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - .env のパース処理は export プレフィックス、クォートされた値（バックスラッシュエスケープ対応）、およびコメント処理をサポート。
    - Paper Trading 向け設定（paper_sqlite_path, paper_fill_mode の妥当性チェックなど）を追加。
    - 各種監視閾値・ファイルパス設定プロパティを追加（pid_file_path, kill_flag_path, cpu/memory/disk thresholds 等）。
  - config_setup.py
    - .env を対話式に作成/更新するウィザード CLI を提供（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等）。
    - 既存 .env の読み込み・マスク表示・保存機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がインストール済みの場合）、本番環境向けの追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START）を追加。
    - `--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全てが 0 の場合のフォールバック挙動を明確化。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄を除外可能、"unknown" セクターは制限非適用）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（`bull/neutral/bear` をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock cap、aggregate cap、cost_buffer を使用した保守的見積もり、スケールダウン時の端数処理（fractional remainder による再配分）を実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを実装。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力を設定。既存ハンドラは再設定時にクリアして二重出力を防止。
    - LOG_DIR 作成失敗時はファイルハンドラをスキップし、stderr に警告を出力してコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定する set_process_priority を実装。Permission不足や未対応 OS の場合は警告を出して無害にフォールバック。
    - プロセスの CPU affinity を固定する set_cpu_affinity を追加（psutil を利用、権限不足は警告でスキップ）。
- データ分析・研究
  - research/factor_research.py（骨格）
    - DuckDB 接続を受けて各種ファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を導入。モメンタム計算関数 calc_momentum の実装を開始（ファイル末尾で補完中/続きあり）。
    - DuckDB を分析用ローカル DB として利用する方針を採用。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL を判定する機能を実装。
    - 日付フィルタ対応（--from/--to）、DB パスは引数/環境変数で指定可能。
    - P95 計算のユーティリティと複数の閾値定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms）を導入。
- DB / 接続
  - DuckDB と SQLite の共存
    - 実行／監視コンポーネントで DuckDB（分析）と SQLite（トランザクション/監視ログ）を並列で使用する構成を導入。
    - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等）。
- その他
  - パッケージ公開用 __all__ に主要サブパッケージを列挙。

Changed
- .env 自動読み込みの挙動
  - OS 環境変数を保護するため、.env 読み込み時に既存の OS 環境変数を上書きしない（.env.local は override=True だが protected により OS 環境は守られる）。
- ログ設定
  - 既存ハンドラの重複を防ぐため、setup_logging は初回に既存ハンドラを flush/close のうえ削除してからハンドラを再設定するよう変更（重複ログ出力回避）。

Fixed
- .env パースの堅牢化
  - export KEY=val 形式、クォート値内のバックスラッシュエスケープ、行末コメント、無効行スキップ等の処理を強化し、一般的な .env フォーマットに対応。
- run_execution の DB 分離
  - paper_trading モード時に本番 DB と混ざらないよう paper_sqlite_path を優先して接続するように修正（データの完全分離を確保）。

Security
- （このリリースでのセキュリティ修正はなし。機密値は .env に保存し、config_setup/README で .env を Git にコミットしない注意を明記）

Notes / Known issues
- research/factor_research.calc_momentum 以下の実装が途中まででファイル末尾が未完（今後補完予定）。
- position_sizing の price フォールバック（価格欠損時に前日終値等を使用する対応）は TODO として残している。
- 一部 API 呼び出し（kabuステーション等）は Mock/実装分離を意識した設計だが、外部環境での実行には各種環境変数の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が必要。

---

参考: 開発者向けコマンド
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]