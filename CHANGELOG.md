# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アーキテクチャとコア機能を実装
  - 自動売買システム "KabuSys" の初期実装。
  - パッケージ公開バージョンを `__version__ = "0.1.0"` として設定。

- 実行用スクリプトおよびエンジン
  - run_execution.py: `ExecutionEngine` 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（`data/paper_trading.db` または環境変数で上書き）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（MockBroker の利用を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンを実行。
    - 停止フラグ (`data/stop_requested.flag`) と PID ファイル (`data/execution.pid`) をサポート。スレッドで `engine.run_session()` を実行し、停止フラグで安全に停止可能。

- 監視用スクリプト
  - run_monitoring.py: `SystemMonitor` のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
    - 監視（monitoring）は環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - 停止フラグ (`data/stop_requested.flag`) を検知してループ終了。

- 設定・環境管理
  - config.py:
    - `.env` 自動読み込み機能（`.env` を優先ではなく OS 環境変数を保護する読み込み順）。
    - `.env.local` による上書き処理、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
    - `.env` 行パーサーの実装（クォート、export プレフィックス、インラインコメントの扱いなどに対応）。
    - `Settings` クラスにプロパティとして各種設定を提供（J-Quants トークン、kabu API、DB パス、paper_trading 用のオプション、監視閾値、環境チェックなど）。
    - `PAPER_FILL_MODE` の入力検証（許容値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証。

  - config_setup.py:
    - 対話式 .env 作成 / 更新ウィザードを実装（秘密値のマスク、デフォルト値、選択肢の検証、保存確認）。
    - `.env` テンプレート書き込み機能を追加。

  - validate_config.py:
    - 起動前設定検証用 CLI を実装（必須環境変数チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証）。
    - PyYAML がない場合は YAML 検証をスキップして警告。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通関数 `setup_logging()` を追加。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py:
    - プロセス優先度設定 `set_process_priority()` を実装（Windows / POSIX に対応、psutil 利用、失敗時は警告してスキップ）。
    - CPU Affinity 設定 `set_cpu_affinity()` を実装（N コアに固定）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - 候補選定 `select_candidates()`（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 `calc_equal_weights()`。
    - スコア加重配分 `calc_score_weights()`（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py:
    - セクター集中制限 `apply_sector_cap()`（既存保有を考慮して特定セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier()`（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知はフォールバック 1.0）。

  - portfolio/position_sizing.py:
    - 発注株数計算 `calc_position_sizes()`。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料/スリッページ見積）を考慮。
      - スケールダウン時は残差に基づく再配分ロジックを実装。

- 研究・ファクター計算
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算方針と関数骨格を追加（DuckDB 経由で prices_daily/raw_financials を参照する設計）。モジュールは関数実装の続きがあるが、基本設計を含む。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値と照合して PASS/FAIL を表示。
    - デフォルト DB パスは `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで上書き可能。
    - P95 計算の実装あり（小さいサンプルでも安全に動作）。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### 注意 / 既知の制約・ TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - 価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある（将来的に前日終値等のフォールバックを検討する旨の TODO コメントあり）。
- portfolio/position_sizing:
  - 将来的な拡張として銘柄毎の lot_size をサポートする予定（現状は全銘柄共通の lot_size を想定）。
- research/factor_research.py:
  - ファイル末尾で関数実装が途中で終わっている（スニペットの途中で途切れている）。完全実装が必要。
- ログディレクトリ作成や psutil による優先度設定は権限/環境に依存し、失敗した場合は警告して機能をスキップする設計。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用」するため、開発環境で使用する場合は意図に注意が必要。
- validate_config は PyYAML が未インストールの場合に YAML の内容検証をスキップする（警告）。

---

差分やバグ修正、改善は次バージョンで追記します。問題・要望があれば issue を作成してください。