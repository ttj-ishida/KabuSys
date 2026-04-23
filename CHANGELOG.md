# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下の履歴は、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし（開発中の変更をここに記載してください）

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 環境・設定管理
  - Settings クラス実装（`kabusys.config`）:
    - 環境変数取得ラッパ（必須変数チェック `_require`、各種プロパティ）。
    - 環境種別検証（development / paper_trading / live）。
    - DB パス、ログレベル、paper trading 用設定、監視閾値などのデフォルトと取得ロジック。
  - .env 自動読み込み機能:
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local のロード順序（OS 環境変数を保護する仕組み）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
  - .env ファイルパーサの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理等。

- 設定ユーティリティ CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）とマスク表示など。
  - `kabusys.validate_config`:
    - 起動前チェック用 CLI を追加（必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパースチェック、live 環境用の注意喚起等）。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行系スクリプト
  - `kabusys/run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - 環境に応じた SQLite 接続分離（paper_trading 時は `paper_sqlite_path` を使用し、本番 DB と分離）。
    - BrokerClientFactory を使ったブローカークライアント生成（paper/live による切替を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動・監視。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理のサポート。
    - RiskManager のデフォルト設定例（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。

  - `kabusys/run_monitoring.py`:
    - SystemMonitor 起動スクリプトを追加。
    - 環境に関わらず監視は本番 sqlite_path を使用する（監視データは共通の monitoring DB へ）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 停止フラグ検出でループ終了、例外時にもログ出力して次ポーリングに継続。

- 監視 DB 初期化 & DuckDB
  - `init_monitoring_db`（参照のみ）を起動時に呼び出して監視用テーブルの存在を保証。
  - DuckDB 連携（`duckdb.connect`）を実行・監視処理や分析処理で利用するための接続確立を追加。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーを統一的に設定するユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/、日次ローテーション、30 日保持）を設定。
    - ログレベル解決順とログディレクトリ作成のフェールオーバー処理を備える。
  - `kabusys.utils.process_priority`:
    - Windows と POSIX を吸収するプロセス優先度設定（psutil ベース）。
    - CPU affinity の設定ユーティリティを追加。
    - 権限不足や未サポート環境でのフォールバック/警告処理あり。

- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 select_candidates（スコア降順、signal_rank タイブレーク）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap（セクター集中上限の適用。売却予定銘柄の除外対応、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier（market regime による投下資金乗数: bull/neutral/bear とフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes（risk_based / equal / score の allocation_method をサポート）。
    - 単元（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）考慮によるスケーリングロジック。
    - 利用可能現金に合わせたスケールダウンと端数配分ロジックの実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から統計を集計して検証レポートを出力する CLI を追加。
    - 指標: 稼働率、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）、リスク却下数 等。
    - デフォルト閾値を定義（稼働率 99%・fill 90%・send 95%・P95 200ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
    - P95 計算、データ不足時の N/A 表示、Fail 判定ロジックを実装。

- 研究モジュール（ファクター計算）
  - `kabusys.research.factor_research`（一部）:
    - モメンタム、MA200、ATR、出来高等のファクター計算方針を実装（DuckDB 接続を使用する設計）。
    - 計算に用いる窓長やスキャン範囲等の定数を定義。

### Changed
- ログ出力の標準ストリームを stdout に統一（cron/タスクスケジューラ環境での扱いやすさ向上）。
- .env の上書き動作を保護（OS 環境変数はデフォルトで上書かない、.env.local で明示的上書き可能）。
- run_monitoring の挙動:
  - 監視は常に本番用 sqlite_path を参照する設計に明示（環境に依存しない監視 DB 利用）。
- run_execution の DB 選択:
  - paper_trading の際は paper_sqlite_path を使用して実運用 DB と分離。

### Fixed
- .env パーサのエッジケース対応（クォート内のバックスラッシュエスケープ、インラインコメント判定など）により誤読を低減。
- ログディレクトリ作成に失敗した場合でも、コンソール出力のみで起動継続するようにし、起動失敗を避けるフェールオーバーを追加。

### Security
- .env を生成する際の注意書きを config_setup に明記（.env を決して Git にコミットしないことを促す）。

---

作者注: 上記は提供されたコードスニペットの内容から推定して作成した CHANGELOG です。実際のリリース履歴やコミットメッセージとは異なる場合があります。必要であれば、実コミット履歴（git log）を基に正確な CHANGELOG を生成できます。