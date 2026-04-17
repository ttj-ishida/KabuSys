# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

- なし（保留中の変更はここに記載します）。

---

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" のベース機能を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 環境/設定
  - 環境変数自動読み込み機能を追加（プロジェクトルートの `.env` と `.env.local` を読み込み、OS 環境変数を保護）。
  - 強力な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを追加し、環境変数の取得・バリデーションを集中管理（KABUSYS_ENV / LOG_LEVEL 等の許容値チェックを含む）。
  - 環境設定ウィザード CLI (`kabusys.config_setup`) を追加。対話式で `.env` を生成・更新可能。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。必須環境変数チェック、パスの存在確認、config/*.yaml のパース検証、`--strict` モードをサポート。

- 実行 / 監視
  - ExecutionEngine 起動スクリプト (`run_execution.py`) を追加。
    - `KABUSYS_ENV=paper_trading` の場合、ペーパートレード用の専用 SQLite（既定: `data/paper_trading.db`）を使用することで本番 DB と完全に分離。
    - 起動前に停止フラグ（`data/stop_requested.flag`）を確認し、既に立っている場合は起動を止める。
    - PID ファイル（`data/execution.pid`）の扱いに対応し、別スレッドでエンジンを実行。停止フラグ検知で安全停止。
  - 監視ループ起動スクリプト (`run_monitoring.py`) を追加。
    - SystemMonitor をポーリングして監視データを SQLite（監視用 DB）に書き込む。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番の sqlite_path を使用する設計（監視 DB の一貫性確保）。

- データベース / 分析
  - DuckDB 統合を追加（分析用 DB として `DUCKDB_PATH` を設定可能、DuckDB 接続をコンポーネントに注入）。

- 実装ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティを追加（`kabusys.utils.process_priority`）。
    - Windows / POSIX を吸収した `set_process_priority(level)`（"high"/"normal"/"low"）を実装。権限や非対応 OS では安全に警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` を追加（指定コア数にプロセスを固定、未対応や権限エラーは警告でスキップ）。
  - 環境変数読み込み時に OS の既存環境変数を保護する仕組みを導入（`.env.local` は上書き、ただし OS 環境変数は保護）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定 / 重み計算 (`kabusys.portfolio.portfolio_builder`)
    - select_candidates（スコア降順・タイブレークロジック）、等配分 / スコア加重配分の関数を追加。
    - スコアが全て 0 の場合に等配分へフォールバックし警告を出す。
  - セクター制限・レジーム乗数 (`kabusys.portfolio.risk_adjustment`)
    - apply_sector_cap：既存保有を考慮したセクター集中制限（max_sector_pct）を実装。unknown セクターは制限対象外。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - ポジションサイズ算出 (`kabusys.portfolio.position_sizing`)
    - risk_based / equal / score ベースの発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング（端数配分ロジック含む）、cost_buffer（スリッページ・手数料想定）対応。

- リサーチ / ファクター計算
  - DuckDB を使ったファクター計算モジュール (`kabusys.research.factor_research`) を追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR、平均売買代金、出来高比）等を SQL + Python で計算。
    - データ不足時の None 扱い、ウィンドウ長条件のチェックなどを実装。

- ツール
  - Paper Trading 向け検証レポート生成スクリプト (`kabusys.tools.paper_verification_report`) を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。
    - DB 存在チェックと例外ハンドリングを実装。期間フィルタ（--from/--to）対応。

### Changed
- 仕様的変更（設計面）
  - .env 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用途）。
  - Settings の各プロパティで入力バリデーションを強化（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。不正値は明確な例外を投げる。

### Fixed
- 安全性 / 安定性
  - MONITOR_POLL_INTERVAL が 0 以下や非整数の場合に time.sleep で ValueError を発生させないよう、検証とフォールバックを実装。
  - プロセス優先度 / CPU affinity の設定で権限エラーや未対応環境が発生した場合は警告ログを出して処理を継続するように変更。
  - Paper verification レポートで該当テーブルが存在しない場合に OperationalError を捕捉してデフォルト値でレポートを生成するよう改善。

### Security
- .env の生成スクリプトに注意喚起を追加：「.env は絶対に Gitにコミットしないこと」を明記。

### Removed / Deprecated
- なし

---

注:
- 上記はリポジトリ内のソースコードから推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。