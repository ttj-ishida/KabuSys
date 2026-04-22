# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」記法に準拠しています。  
バージョニングはセマンティックバージョニングに従います。

注: 以下の履歴はリポジトリ内のソースコード（CLI、モジュール、コメント等）から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-22

初回リリース。主に自動売買システム「KabuSys」のコア機能および運用用ユーティリティを含みます。

### Added
- パッケージメタ情報
  - __version__ = "0.1.0" を追加。

- 設定管理
  - 環境変数読み込み・ラッパーを提供する `kabusys.config.Settings`。
    - .env 自動読み込み（プロジェクトルートの .env → .env.local、OS 環境変数優先）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 各種設定プロパティ（J-Quants トークン、kabu API 設定、DB パス、監視閾値、環境判定等）。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）。
    - `KABUSYS_ENV`、`LOG_LEVEL` の値チェック。

- 環境セットアップ・検証CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を生成・更新する CLI。
    - `.env` の読み書き機能、既存値の再利用、シークレット項目のマスク表示。
  - `kabusys.validate_config`：起動前チェック CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリチェック。
    - `config/*.yaml` の存在確認（PyYAML がなければ検証をスキップして警告）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ログ・プロセスユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - コンソール（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化して標準出力のみで継続。
  - `kabusys.utils.process_priority`：
    - `set_process_priority(level)`：Windows / POSIX を吸収してプロセス優先度を設定。
    - `set_cpu_affinity(cpu_count)`：プロセスを最初の N コアに固定（実行環境依存でスキップされることがある）。
    - エラー発生時は警告を出して安全にフォールバック。

- 実行・監視用エントリポイント
  - `run_execution.py`：
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (`data/execution.pid`) の扱い。
    - RiskConfig のデフォルト値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 等）を設定。
  - `run_monitoring.py`：
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト60秒）によりポーリング間隔を上書き可能。0 以下や不正値はデフォルトにフォールバックして警告。
    - 監視用 DB（SQLite）は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB の path に保存）。
    - 停止フラグ検知でループ終了、例外時はログを残して次ポーリングまで待機。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db`（起動スクリプト内で呼び出し）により監視テーブルが存在することを保証（冪等）。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates（スコア順で候補選定）、calc_equal_weights、calc_score_weights（スコア加重、全スコア 0 の場合等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap（セクター集中制限。既存ポジションの評価額からセクターが上限超過なら新規候補を除外。unknown セクターは適用しない）。
    - calc_regime_multiplier（market regime に応じた投下資金乗数。bull/neutral/bear に対応、未知値は 1.0 でフォールバック）。
    - apply_sector_cap に price 欠損時の将来的フォールバックに関する TODO（コメントで注意喚起）。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes（allocation_method = "risk_based" | "equal" | "score" をサポート）。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）反映、残差処理（lot 単位で端数を復元するロジック）。
    - 将来の拡張として銘柄毎 lot_size を想定する TODO コメントあり。

- 研究・分析用モジュール（下流処理用）
  - `kabusys.research.factor_research`（ファクター計算の骨格）：
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、ATR、流動性指標等を想定した計算ロジックの設計方針と定数を定義。
    - DuckDB 接続を受け、prices_daily/raw_financials を参照して計算する設計（実装はモジュール内に記載の関数群を含む、部分的に実装）。
    - （ファイルは一部実装が続く想定だが、提供コードは途中まで含む）

- 運用ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用検証レポート生成スクリプト（CLI）。
    - 日付レンジ指定（--from/--to）や DB パス（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）を受け付ける。
    - システム稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルトの閾値をコード内で定義（例: 稼働率 >= 99.0%、fill_rate >= 90% 等）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （なし）

---

注意・既知事項
- apply_sector_cap や position_sizing 内に「price が欠損した場合」の挙動や将来の拡張（銘柄別 lot_size）に関する TODO コメントがあります。運用前に価格取得の確実性やデータフォールバック戦略を確認してください。
- validate_config は PyYAML が未インストールの場合 YAML の中身検証をスキップして警告を出します。YAML 検証を有効にしたい場合は PyYAML をインストールしてください。
- logging_setup はログディレクトリ作成に失敗するとファイル出力を無効化します（stdout のみ）。デプロイ先のファイル権限・パスの存在を確認してください。
- run_monitoring は監視用 DB を「環境にかかわらず」Settings.sqlite_path（本番想定パス）に接続します。監視データをテスト環境と分離したい場合は設計の取り扱いに注意してください。
- factor_research は設計方針と一部の実装を含みますが、完全な実装（全ファクター算出・正常系ハンドリング）の確認が必要です。

もし CHANGELOG に追記したい差分や、より細かいコミット単位の履歴（例えばファイルごとの追加日やコミットメッセージ）があれば、それに合わせてリリースノートを分割・拡張します。