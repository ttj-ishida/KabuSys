# CHANGELOG

すべての変更は「Keep a Changelog」形式に従って記載しています。

履歴の内容はリポジトリ内のソースコードから推測して作成しています（実際のコミット履歴ではありません）。各項目は機能追加・改善・不具合修正などをコードの実装から読み取った注記です。

## [Unreleased]

（当面の未リリース変更はありません）

---

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム「KabuSys」の基本機能一式を収録。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境・設定管理
  - Settings クラスを実装（`kabusys.config`）。
    - 環境変数から各種設定を取得するプロパティ群を提供（J-Quants / kabu API / DB パス / monitoring 閾値 / 実行環境 など）。
    - `KABUSYS_ENV` の検証（development, paper_trading, live）。
    - `PAPER_FILL_MODE` の検証（instant, partial, never, reject）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動 .env ロード無効化対応。
  - .env 自動ロード実装：
    - プロジェクトルートを .git または pyproject.toml から探索して `.env` / `.env.local` を読み込み。
    - `.env` のパースは `export KEY=val`, クォート、エスケープ、インラインコメント等に対応する堅牢な実装。

- 設定ユーティリティ
  - 対話式設定ウィザード（`kabusys.config_setup`）を追加。
    - `.env` の新規作成・更新をサポート。秘密値はマスク表示。
    - デフォルト値や選択肢を用意し、保存前の確認ダイアログを提供。
  - 設定検証コマンドラインツール（`kabusys.validate_config`）を追加。
    - 必須/任意環境変数チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および YAML パース確認（PyYAML が存在する場合）。
    - `--strict` オプションで警告を FAIL 扱いにする機能。
    - live 環境向けの追加ガード（LINE 通知未設定や Kill Switch 設定の警告）。

- 実行スクリプト
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値の際はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する仕様（明示的）。
    - 停止フラグファイル（data/stop_requested.flag）の検知機構を備え、フラグ検知でループを終了。
    - SystemMonitor 初期化および単一チェック `check_once()` 実行をループで呼び出し、例外時はログに記録して次のポーリングへ継続。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper DB（デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（本番/モック切替）。
    - ExecutionEngine の組み立てとデーモンスレッドでのセッション実行、停止フラグ監視（stop flag による安全停止）を実装。
    - 起動時に pid ファイルを扱うための pid_file パスを注入。

- 実行補助ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時のフォールバック（ファイル出力無効化）に対応。
    - 環境変数 `LOG_LEVEL` / `LOG_DIR` を用いた設定解決。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する機能 `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS 時に安全にスキップして警告ログを出す堅牢な実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナル候補選択 `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（スコア合計が 0 の場合は等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限適用 `apply_sector_cap`（既存持株を考慮して同一セクター新規候補を除外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear とフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算 `calc_position_sizes`（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した実装。
    - risk_based 計算では stop_loss_pct / risk_pct を用いたリスクベースの株数算出を実装。
    - aggregate スケールダウン時に残余を lot 単位で配分するアルゴリズムを実装。

- 解析・リサーチ
  - `kabusys.research.factor_research` を追加（モメンタム・ボラティリティ等のファクター計算の骨子を実装）。
    - DuckDB 接続を受け取り prices_daily 等のテーブルから計算する設計。
    - モメンタム（1M/3M/6M、MA200乖離）、ATR、出来高系指標などを想定。関数雛形と定数を用意。

- ツール
  - Paper Trading 向け検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - 指定期間（--from / --to）や DB パス（--db / env）を受け取り、system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - 合否判定の閾値を定義（稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - DB のテーブル欠如や空データに対して耐性を持つ実装（OperationalError をキャッチして N/A を扱う）。

- データベース補助
  - 監視 DB 初期化ユーティリティ `init_monitoring_db` を各起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力の一貫化
  - 全起動スクリプトは `setup_logging(app_name=...)` を呼んで統一的にログ設定を行うようになっている（ログ名に応じてファイル出力先を分離）。

- 実行時のプロセス制御
  - 起動直後にプロセス優先度を High に設定する設計を導入（`set_process_priority("high")` を run_monitoring/run_execution で実行）。

- .env 読み込み挙動
  - OS 環境変数を保護しつつ `.env.local` で上書き可能にする読み込み順序を採用（OS 環境 > .env.local > .env）。

### Fixed
- 例外・エラー耐性の向上
  - 監視ループ内 `monitor.check_once()` 実行時に発生する予期しない例外はログに例外情報を出してループ継続するよう変更（システム安定性のため）。
  - run_execution のスレッド制御で停止フラグを検知した際にエンジンを安全に停止する処理を追加。
  - logging_setup はログディレクトリ作成に失敗してもコンソール出力のみで継続するようにフォールバック。

### Security
- .env に関する注意喚起をウィザードの出力に明記（.env を絶対に Git にコミットしないこと）。

### Notes / Migration
- `KABUSYS_ENV=paper_trading` を使用する場合、paper_trading 用の SQLite DB（デフォルト `data/paper_trading.db`）が使用され、本番監視 DB（monitoring.db）とは分離されます。運用環境では環境変数と `.env` の設定を `kabusys.config_setup` と `kabusys.validate_config` で事前に確認してください。
- `MONITOR_POLL_INTERVAL` は秒数（整数）を環境変数で指定できます。不正値や 0 以下を指定するとデフォルト（60 秒）にフォールバックします。
- `PAPER_FILL_MODE` の指定値は "instant" | "partial" | "never" | "reject" のいずれかでなければならないため、本番運用前に設定を確認してください。

---

（以降のバージョンはこのファイルに追記していってください）