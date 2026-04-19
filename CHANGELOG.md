# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（現時点で未リリースの作業や既知の TODO / 進行中の機能はここに記載します）
- research/factor_research.py が未完成（ファイル末尾で途中終了）。ファクター計算モジュールの実装継続予定。

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を含む最小限の実装を提供します。

### Added
- パッケージ基盤
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開インターフェース: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 設定管理
  - 環境変数/`.env` 読み込み機能（`kabusys.config`）
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 自動で `.env` と `.env.local` を読み込む（OS 環境変数を保護）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `.env` 行のパーサ `_parse_env_line` が以下に対応：
      - `export KEY=val` 形式
      - シングル・ダブルクォートで囲まれた値（バックスラッシュエスケープ対応）
      - クォートなしのインラインコメント処理（`#` の扱い）
    - 設定取得用 `Settings` クラスを提供。各種プロパティ経由で値を取得（J-Quants トークン、kabu API パスワード、DB パス、監視閾値、環境種別判定等）。
    - Paper Trading 関連:
      - `paper_sqlite_path`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）
      - `paper_fill_mode` を導入（有効値: "instant" | "partial" | "never" | "reject"。不正値は例外）
    - プロセス制御用パス（pid ファイル、kill/stop フラグ等）をプロパティで取得。

- .env 作成ウィザード CLI
  - `kabusys.config_setup` を追加。対話式ウィザードで `.env` の初期作成・更新が可能。
  - シークレット項目は入力確認時にマスク表示。デフォルト / 選択肢を提示して保存可能。
  - 書式整形済み `.env` ヘッダを出力 (.env は Git にコミットしない旨を明記)。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。起動前に必須環境変数や config/*.yaml、DB パス等を検証。
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出力。
  - `--strict` オプションで警告を FAIL 扱い（exit 1）。

- 実行エンジン / 監視
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite を使用して本番 DB と分離。
    - Broker クライアント生成（BrokerClientFactory）、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - `run_monitoring.py`
    - SystemMonitor 用のポーリングループ起動スクリプト。プロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告。
    - 監視 DB（sqlite）は常に `Settings.sqlite_path` を使用する（環境に依存せず本番監視 DB を参照）。
    - stop フラグ検知でループを終了。check_once() 内の例外はキャッチしてログ出力しループ継続。

- DB / 分析
  - sqlite3 と DuckDB の接続を利用（`init_monitoring_db` による監視テーブル初期化は冪等）。
  - DuckDB は分析用（prices_daily / raw_financials 等を想定）。

- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - 既存ハンドラをクリアして多重設定を防止。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - `kabusys.utils.process_priority`
    - psutil を利用して Windows / POSIX の差を吸収。`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応 OS の場合は警告を出力して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重（全スコア 0 の場合は等分配にフォールバック、警告）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター露出を算出し、上限超過セクターの候補を除外）。売却予定コードを露出計算から除外可能。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知のレジームは警告して 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数計算。
    - lot_size（単元株）処理、max_position_pct/max_utilization 等の上限、コストバッファ(cost_buffer) を考慮した aggregate cap のスケーリング、端数処理のための再配分ロジックを実装。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用検証レポート生成スクリプト。SQLite の paper_trading DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等の指標を算出して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ（--from / --to）、DB パス指定 (--db) に対応。
    - デフォルトの閾値（稼働率 >= 99%、注文成功率 >= 90% 等）を定義。

### Changed
- ロギング
  - コンソール出力は stderr ではなく stdout を使用するよう統一（cron / scheduler とリダイレクト運用を考慮）。
  - 既存ハンドラを一度 flush/close してから削除し再設定することで多重登録を防止。

- .env 読み込み順序の明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は override=True）。

### Fixed
- 環境変数の扱い
  - `_parse_env_line` によるクォート・エスケープ処理を強化し、誤ったコメント切り取りやエスケープ文字の扱いによる誤読を防止。

- 監視 / 実行の堅牢化
  - run_monitoring のポーリングループで check_once() 内の例外をキャッチしてループ継続するようにし、監視プロセスが単一の例外で停止しないように修正。
  - run_execution/run_monitoring ともに起動直後にプロセス優先度を設定するように統一。

### Known issues / Notes
- research/factor_research.py は未完（ファイル末尾が途中で切れている）。ファクター計算（モメンタム等）の実装が継続中。
- position_sizing の price フォールバックについて注記あり（price が欠損した場合に露出が過少評価される可能性があるため、将来的に前日終値等のフォールバック導入を検討）。
- ログディレクトリ作成に失敗するとファイルハンドラは使用されないが、コンソール出力は維持される（意図的なフォールバック動作）。

---

履歴は今後のリリースで更新していきます。リリースノートに記載したくない小さな内部変更やリファクタはここに逐次追加してください。