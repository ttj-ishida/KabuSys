# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット:
- 反映済みのリリースはバージョン見出しを持ちます。
- 各リリースは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで記載します。

## [0.1.0] - 2026-04-21
初回リリース — 基本的な自動売買基盤と運用ツール群を実装。

### Added
- 基本パッケージ
  - パッケージ名: `kabusys`、バージョン定義 `__version__ = "0.1.0"` を追加。

- 起動スクリプト
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止はプロジェクト直下 `data/stop_requested.flag` ファイルの存在で検出。
    - 監視は環境（`KABUSYS_ENV`）に関わらず本番用の `sqlite_path` を使用する設計。
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するスクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - Broker の取得は `BrokerClientFactory` を利用。エンジンはスレッドで起動し、停止フラグで安全に終了可能。
    - 実行用 PID ファイル管理（`data/execution.pid`）をサポート。

- 設定・環境変数管理
  - `src/kabusys/config.py`
    - .env 自動読み込み機能（`.env` と `.env.local`、OS 環境変数優先、多重読み込み保護）。
    - プロジェクトルート探索ロジック（`.git` または `pyproject.toml` を基準）により CWD に依存しないロード。
    - 強力な .env パーサ（クォート、エスケープ、コメント処理、`export KEY=...` に対応）。
    - `Settings` クラスを導入し、J-Quants/Kabu API/Coinfig 等の設定をプロパティ経由で提供。
    - Paper Trading 関連設定（`paper_sqlite_path`, `paper_fill_mode`）を追加。`paper_fill_mode` の検証（有効値: `instant|partial|never|reject`）。
    - 監視・Kill Switch などの閾値/パス設定（`pid_file_path`, `kill_flag_path`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct` 等）。
    - 環境フラグ判定プロパティ（`is_live`, `is_paper`, `is_dev`）。

- 設定用 CLI / ウィザード / 検証
  - config_setup: `src/kabusys/config_setup.py`
    - 対話式ウィザードにより `.env` を初期作成 / 更新するユーティリティを追加。
    - シークレット入力の扱い、選択肢、既存値の再利用、生成される `.env` のテンプレートを実装。
  - validate_config: `src/kabusys/validate_config.py`
    - 起動前に `.env` と `config/*.yaml` を検証する CLI を追加。
    - 必須環境変数チェック、`KABUSYS_ENV` の妥当性、ログレベル、DB パスの親ディレクトリチェックを実装。
    - PyYAML が存在しない場合は YAML 検証をスキップする旨の警告を出力。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ周りユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 全起動スクリプトで統一して使う `setup_logging(app_name, log_dir, level)` を実装。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日分保持）を設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。

- プロセス優先度管理
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォーム（Windows/Linux/macOS 等）でプロセス優先度を設定する `set_process_priority(level)` を実装（`high|normal|low`）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を追加。
    - psutil ベースで実装し、許可権限がない場合は警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でブレーク）を実装。
    - 重み算出: `calc_equal_weights`, `calc_score_weights`（スコア総和が 0 の場合に等金額配分へフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中排除 `apply_sector_cap`（既存ポジションからのセクター比率を計算、閾値超過のセクターの新規候補を除外）。
    - 市場レジームに基づく乗数 `calc_regime_multiplier`（`bull=1.0, neutral=0.7, bear=0.3`、未知レジームは警告の上 1.0 でフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 株数算出ロジック `calc_position_sizes` を実装（`risk_based`, `equal`, `score` の各方式をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限・総投下上限（available_cash）に合わせたスケールダウン処理、cost_buffer を考慮した保守的見積りを実装。
    - スケールダウン時に端数処理（remainders）を考慮して lot 単位で追加配分。

- リサーチ / ファクター計算（骨格）
  - `src/kabusys/research/factor_research.py`
    - モメンタム/ボラティリティ/流動性/バリュー等のファクター計算モジュールの設計と一部実装（DuckDB を用いた prices_daily / raw_financials 参照での計算を想定）。
    - 定数・期間定義（例: 1M/3M/6M、MA200、ATR20 など）を追加。
    - 関数インターフェース設計（例: `calc_momentum(conn, target_date)`）。

- 運用ツール
  - Paper Trading 検証ツール: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite のログを解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。
    - デフォルト閾値を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。

- DB 関連
  - 実行/監視処理で SQLite（監視用）と DuckDB（分析用）へ接続する処理を追加。
  - 監視 DB の初期化を行う `init_monitoring_db(sqlite_conn)` を起動前に実行（冪等）。

### Changed
- 設計方針・セキュリティ配慮
  - Paper Trading と本番 DB を明確に分離（`PAPER_TRADING_SQLITE_PATH` / `paper_sqlite_path`）し、テスト・検証時の誤操作リスクを低減。
  - `.env` の自動ロードは OS 環境変数を保護（`protected`）しつつ `.env.local` により上書き可能な設計。

### Fixed
- 簡易なフォールトトレランスを追加
  - run_monitoring のメインループ内で `monitor.check_once()` が例外を投げてもログ出力してループ継続するように保護。
  - run_execution のスレッド監視ループで停止フラグ検出時に `engine.stop()` を呼び出して安全に終了するフローを実装。
  - logging_setup: ログディレクトリの作成失敗やファイルハンドラ作成失敗を安全に処理してコンソールログへフォールバック。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報（API トークンやパスワード）は `.env` に保存する設計だが、`config_setup` の README で `.env を絶対に Git にコミットしないこと` を明示している。

---

注意:
- present なコードは多くのユーティリティ、アルゴリズムの基本設計と実装を含みますが、実運用で必要な追加の検証（単体/統合テスト、エラーケースの網羅、外部 API の契約確認等）は推奨されます。
- `research/factor_research.py` はファイル末尾で途中実装の可能性があり（スニペットが途中で終了）、完全実装は今後の作業項目です。