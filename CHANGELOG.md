# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初期リリース（コードベースから推測）をまとめています。

注: 日付はコード解析時点の推測日です。

## [0.1.0] - 2026-04-21

### Added
- 全体
  - プロジェクト初期実装として主要コンポーネントを追加。
  - パッケージメタ情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として管理。

- 実行/監視ランナー
  - `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度を設定して（High）、SQLite / DuckDB に接続し、ExecutionEngine をバックグラウンドスレッドで起動・監視する。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用することで本番 DB と完全分離。
    - 停止フラグファイル (`data/stop_requested.flag`) を監視し、安全に停止できる仕組みを実装。
    - 実行時 PID ファイル（`data/execution.pid` デフォルト）を利用。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番の `sqlite_path` を使用する（設計上の注意）。

- 設定管理 / ウィザード / 検証
  - `src/kabusys/config.py`
    - 環境変数・設定を読み込む Settings クラスを追加。自動でプロジェクトルートの `.env` / `.env.local` を読み込み（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` でスキップ可能）。
    - `.env` の読み込みは OS 環境変数を保護（上書き禁止）する仕組みを採用。
    - 各種設定（DB パス、API トークン、Paper Trading 用設定、監視しきい値など）をプロパティとして提供。値検証（例: `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL`）を実施。
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加。必須項目・オプション項目を対話的に入力可能。生成される `.env` に対して「Git にコミットしない」旨をコメントで明示。
  - `src/kabusys/validate_config.py`
    - `.env` と `config/*.yaml` の基本的な検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）などを実施。`--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - BUY シグナルの候補選定（スコア順、タイブレークに signal_rank）と等分配 / スコア加重重み計算関数を追加。スコアが全て 0 の場合は等金額配分へフォールバック（警告出力）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中（apply_sector_cap）や市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知のレジームはフォールバックで 1.0（警告）。
    - `apply_sector_cap` は既存保有のセクター暴露を計算し、上限超過セクターの新規候補を除外。`unknown` セクターは除外対象外。
  - `src/kabusys/portfolio/position_sizing.py`
    - position-sizing ロジックを追加。`risk_based` と `equal/score` の allocation_method をサポートし、単元株（lot_size）で丸め、1銘柄上限や aggregate cap によるスケーリング、コストバッファ（手数料・スリッページ見積）を考慮した調整を実装。
    - aggregate スケーリング時に端数を lot_size 単位で再配分するアルゴリズムを実装。

- リサーチ / ファクター計算（部分実装）
  - `src/kabusys/research/factor_research.py`
    - DuckDB を用いたファクター計算の基盤を追加。モメンタム・ボラティリティ・流動性・バリュー等の設計方針と定数が定義され、モメンタム計算関数（calc_momentum）の実装を開始（ファイル末端が未完である可能性あり）。

- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 統一的なログ設定ユーティリティを導入。stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/`、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（psutil ベース）。nice 値や Windows の優先度クラスを利用し、権限不足等で失敗した場合は警告を出してスキップする。CPU アフィニティ設定関数も提供。

- 実行コンポーネント（Execution 内）
  - Execution に必要なファクトリやマネージャー（`BrokerClientFactory`, `ExecutionEngine`, `OrderManager`, `OrderRepository`, `Reconciler`, `RiskManager` など）の組み立てを run_execution で実行。RiskManager のデフォルト設定には circuit-breaker などを含む。

- モニタリング DB 初期化
  - `init_monitoring_db` を用いて monitoring 用テーブルが存在することを保証（冪等）。

- Tools
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定。DB パスは引数 `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

### Changed
- n/a（初期リリース：なし）

### Fixed
- 環境変数パーサの堅牢化（`src/kabusys/config.py`）
  - .env の行パースでクォートとバックスラッシュエスケープ、インラインコメント処理に対応。`export KEY=...` 形式をサポート。
  - `.env.local` 読み込み時に OS 環境変数を保護するための protected set を導入。

- ログ周りのフォールバック強化
  - `logging_setup` はログディレクトリの作成失敗やファイルハンドラ作成の失敗を想定して、コンソール出力のみで継続するように実装。

- プロセス優先度設定でのプラットフォーム差分吸収
  - Windows と POSIX の差を吸収し、未対応 OS や権限不足時に安全にスキップする実装。

### Removed
- n/a（初期リリース：なし）

### Deprecated
- n/a（初期リリース：なし）

### Security
- `.env` 生成時に「絶対に Git にコミットしないこと」を明記（`config_setup.py` の生成ヘッダ）。  
- Secrets（API トークン等）はウィザードでマスク表示（表示は ****）。

### Notes / Known issues / TODOs
- `src/kabusys/research/factor_research.py` の末尾が途中で終了している（calc_momentum の実装が途中）ため、リサーチ機能は未完の可能性あり。今後の実装・テストが必要。
- `position_sizing` の価格フォールバック（価格が 0.0 の場合の扱い）について TODO コメントあり。前日終値や取得原価等のフォールバック戦略の追加を検討。
- いくつかの機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。環境により追加インストールが必要。
- Monitoring は「環境にかかわらず本番 sqlite_path を使用する」設計上の注意点あり。必要に応じて運用ドキュメントで明記することを推奨。

---

上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。追加のコミット履歴や開発ノートがある場合は、それらに合わせてバージョン/日付/項目を更新してください。