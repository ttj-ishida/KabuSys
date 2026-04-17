# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはリポジトリの現状ソースコードから推測して作成した初期リリース向けの変更履歴です。

全体方針:
- バージョンはパッケージ内の __version__ を基に 0.1.0 としています。
- 日付は本作成日（2026-04-17）を使用しています。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージと CLI / ユーティリティ群を追加。
  - パッケージ情報: `kabusys.__version__ = "0.1.0"`.
- 環境設定 / 管理
  - Settings クラス (`kabusys.config.Settings`) を導入し、環境変数から各種設定（DB パス、API トークン、監視閾値、実行環境など）を安全に取得できるようにした。
  - 自動 .env ロード機能を実装（プロジェクトルート自動検出、.env / .env.local の読み込み）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env の行パースロジックを強化（export プレフィックス、クォート済み値、インラインコメント、エスケープシーケンスに対応）。
  - `kabusys.config_setup`：対話式ウィザードで .env を作成/更新する CLI を追加（シークレットのマスク表示、既存値の再利用、ファイル書き込み）。
  - `kabusys.validate_config`：.env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、PyYAML があれば YAML のパース検証、live 環境向けの追加ガード等を実施。`--strict` オプションで警告を FAIL 扱いに可能。
- 実行系 / 監視
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用して本番 DB と分離。
    - Broker の生成は `BrokerClientFactory` を介して抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、スレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) による外部停止に対応。
    - ExecutionEngine 起動前に監視テーブルを冪等に初期化 (`init_monitoring_db`)。
  - `run_monitoring.py`：SystemMonitor ポーリング起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値はデフォルトにフォールバックし警告を出す。
    - Monitoring は実行環境にかかわらず本番の `sqlite_path` を使用する設計（監視用 DB の一貫性を想定）。
    - 停止フラグ / PID ファイルの取り扱い。
- 監視 DB 初期化ユーティリティ `kabusys.monitoring.monitoring_db.init_monitoring_db` を起動時に利用（監視テーブルの存在保証）。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows / POSIX の差を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
  - CPU affinity 設定ユーティリティ `set_cpu_affinity` を追加（利用コア数の固定）。
  - 権限不足や未対応 OS に対する安全なフォールバックとログ出力を実装。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：シグナル選別 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコア合計が 0 の場合は等分配にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`：セクター集中度の上限適用 (`apply_sector_cap`) と市場レジームに応じた資金乗数 (`calc_regime_multiplier`) を実装。未知レジームはフォールバック（1.0）して警告。
  - `kabusys.portfolio.position_sizing`：ポジションサイズ決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。単元株 (lot_size) 切り上げ・切り捨て、1銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）、残差分の lot 単位での再配分等を実装。価格欠損や負荷値に対する安全弁とデバッグログを追加。
- 研究 / ファクター計算
  - `kabusys.research.factor_research`：DuckDB を用いたファクター計算モジュールを追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20、相対ATR）、流動性（20日平均出来高 等）を計算する関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード結果の検証レポートを生成する CLI を追加。
    - デフォルト DB は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）。
    - 指標：稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。P95 は標本から計算。
    - 合格基準（閾値）を定義: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。判定は PASS/FAIL として出力。
    - 日付範囲の絞り込みオプション（--from, --to）をサポート。コマンドラインオプションで DB パス指定可能。
- その他
  - パッケージエクスポートを `kabusys.portfolio.__init__` で整理。
  - 空の `kabusys.tools.__init__` を追加（tools パッケージ化）。

### Changed
- なし（初回リリースとして新規追加中心のため）。

### Fixed
- なし（初回リリース）。

### Notes / Implementation details / 備考
- 環境変数のデフォルトや既定値:
  - MONITOR_POLL_INTERVAL: 60 秒（run_monitoring）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH 等は Settings から取得可能（デフォルト値あり）。
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ許容（不正値は例外）。
- セーフティ設計:
  - run_execution/run_monitoring は外部ファイル（data/stop_requested.flag）を監視して安全に停止できる。
  - process_priority / cpu_affinity は権限不足・未対応環境時に警告を出してスキップする。
  - DB 初期化（監視用テーブル）は冪等で実行。
- ログレベルや本番環境に関する注意喚起:
  - validate_config は KABUSYS_ENV=live の際に LINE 通知設定や Kill Switch 設定等の注意を警告する。

今後の想定追加・改善点（候補）
- ExecutionEngine / Broker 実装の詳細なテストカバレッジ追加。
- 銘柄ごとの lot_size を stocks マスタで管理する拡張（コメントに TODO あり）。
- 価格欠損時のフォールバック価格（前日終値等）を導入してエクスポージャー計算精度を向上。
- factor_research の追加ファクター・正規化ユーティリティ統合（kabusys.data.stats との連携）。

--- 

（本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、実装担当者による確認・追記をお願いします。）