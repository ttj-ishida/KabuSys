# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

※ この CHANGELOG は提示されたコードベースから実装内容を推測して作成しています。

## [Unreleased]

（なし）

---

## [0.1.0] - 初回リリース
最初の公開リリース。自動売買システム KabuSys の基礎機能群を実装しています。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタ情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 実行用スクリプト
  - `run_monitoring.py`
    - システム監視ループを起動するスクリプト。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 停止制御のためにプロジェクト配下 `data/stop_requested.flag` を監視。
    - 起動時にプロセス優先度を `High` に設定。
    - SQLite（監視 DB）と DuckDB へ接続し `SystemMonitor` を使用してチェックを実行。
    - 監視は環境（`KABUSYS_ENV`）にかかわらず本番用 `sqlite_path` を使用する設計。

  - `run_execution.py`
    - 注文実行エンジン（ExecutionEngine）を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用に Mock ブローカーを使用し、専用の DB（`data/paper_trading.db`）で完全分離。
    - 起動時にプロセス優先度を `High` に設定。
    - エンジンは別スレッドで実行し、停止フラグ検知で安全に停止。
    - PID 管理（`data/execution.pid`）をサポート。

- 設定・環境変数管理
  - `config.py`
    - `.env` 自動読み込み（プロジェクトルートから `.env` / `.env.local` を読み込む。既存 OS 環境変数は保護）。
    - `.env` パース機能の強化: `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - 各種設定プロパティを実装（J-Quants, kabuステーション, LINE, DuckDB/SQLite パス, pid/kill フラグパス, モニタ閾値, 環境判定 `is_live`/`is_paper`/`is_dev` など）。
    - `PAPER_FILL_MODE` のバリデーション（有効値: `"instant"|"partial"|"never"|"reject"`）。
    - `PAPER_TRADING_SQLITE_PATH` によるペーパートレード用 DB パス上書き。

  - `config_setup.py`
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI。
    - 必須/任意項目のプロンプト、シークレットマスク表示、保存前の確認、`.env` のテンプレート書き出しを実装。

  - `validate_config.py`
    - 起動前に設定（環境変数、config/*.yaml）を検証する CLI。
    - 必須環境変数チェック (`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`)。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証、DB パスの親ディレクトリチェック、YAML ファイルの存在・パース検査（PyYAML が無ければ警告）。
    - `--strict` フラグで警告も失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE トークン未設定や `KILL_FLAG_CLEAR_ON_START` の危険設定に関する警告）。

- ログ・プロセスユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに対してコンソール出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を統一的に設定するユーティリティ。
    - `LOG_LEVEL` / `LOG_DIR` / 引数 `level`/`log_dir` による設定の解決順を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - `utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度（`high|normal|low`）を設定。
    - `psutil` を用いた実装で権限不足などの例外は警告でスキップ。
    - CPU affinity 固定機能 `set_cpu_affinity` を追加（最初の N コアにピン留め）。

- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - 銘柄候補選定 `select_candidates`（スコア降順、signal_rank によるタイブレーク）。
    - 等分配 `calc_equal_weights`、スコア加重 `calc_score_weights`（スコア合計 0 の場合は等分配へフォールバック）。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`（既存保有比率が閾値超過のセクターの新規候補を除外。`unknown` セクターは無制限）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（`bull`=1.0, `neutral`=0.7, `bear`=0.3、未知のレジームは警告後 1.0 をフォールバック）。

  - `portfolio/position_sizing.py`
    - 発注株数計算 `calc_position_sizes`。
    - アロケーション方式: `risk_based`（リスク割合・ストップロスに基づく）および `equal`/`score`。
    - 1銘柄上限（`max_position_pct`）、口座全体の利用上限（`max_utilization`）を考慮。
    - 単元株（`lot_size`）で丸め、コストバッファを考慮した aggregate cap スケーリングと残差分配ロジックを実装。
    - 価格欠損時のスキップやログ出力（デバッグ）を実装。

  - `portfolio/__init__.py`
    - 上記機能をパッケージとしてエクスポート。

- 解析・リサーチ
  - `research/factor_research.py`（ファクター計算モジュールを実装開始）
    - Momentum, Value, Volatility, Liquidity の設計方針と定数定義を追加。
    - DuckDB 接続を受け取り `prices_daily` / `raw_financials` を参照してファクターを計算する方針。
    - モメンタム計算関数 `calc_momentum` の署名と docstring（実装途中の箇所あり）。

- ツール群
  - `tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI。
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL を判定する閾値を定義。
    - `P95` 計算、期間フィルタ（--from / --to）および `--db` オプションをサポート。

- 監視 DB 初期化
  - `monitoring/monitoring_db.py`（参照されているがソースは省略）を利用して監視テーブルを初期化する呼び出しを各起動スクリプトに組み込み（冪等）。

### 変更 (Changed)
- 起動スクリプトの設計
  - 監視ループは停止フラグ（`data/stop_requested.flag`）の存在を定期チェックして安全に終了するように統一。

- ロギング設計方針
  - コンソール出力は `stdout` を使用（stderr ではない） — cron/Task Scheduler でのログリダイレクトを想定。

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 (Notes)
- `.env` ファイルは機密情報を含むため Git にコミットしてはいけない旨を `config_setup.py` が強調。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定することで自動 `.env` ロードを無効化可能（テスト用途）。
- `validate_config` は PyYAML がない環境では YAML の内容検査をスキップするが警告を出力する。
- `research/factor_research.py` の一部関数は実装途中（スニペット末尾が切れているため、追加実装が必要）。

---

参照:
- 主要 CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.run_monitoring
  - python -m kabusys.run_execution
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

この CHANGELOG はコードベースの内容から推測して作成されています。実際のコミット履歴やリリースノートと差異がある場合は、適宜差し替えてください。