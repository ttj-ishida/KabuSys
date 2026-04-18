# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。互換性のない変更は Breaking Changes として明記します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 環境設定・読み込み
  - プロジェクトルートを `.git` または `pyproject.toml` から探索して自動で `.env` を読み込む仕組みを実装（src/kabusys/config.py）。
  - `.env` ファイルのパース機能を実装（クォート・エスケープ・コメント処理に対応）。未設定キーは保護された OS 環境変数を上書きしないよう配慮。
  - 各種設定値を取得する `Settings` クラスを追加（DB パス、API トークン、監視閾値、環境種別など）。
  - `PAPER_FILL_MODE`（paper trading の模擬約定モード）や `PAPER_TRADING_SQLITE_PATH` 等の設定取得ロジックを実装。`PAPER_FILL_MODE` は "instant" / "partial" / "never" / "reject" を受け付け、不正値は例外。

- 設定ウィザード CLI
  - `.env` の対話的作成・更新を行う `config_setup` CLI を追加（src/kabusys/config_setup.py）。
  - 秘匿値は表示時マスク、既存値の再利用、選択肢サポート、保存前の確認などのUXを提供。
  - `.env` 書き出しテンプレートを用意（説明コメント付き、Git にコミットしない旨の注意）。

- 設定検証 CLI
  - `.env` と `config/*.yaml` の事前検証を行う `validate_config` CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在チェック、PyYAML がある場合は YAML のパース検証を実施。
  - `--strict` オプションで警告を失敗（exit 1）扱いにするモードを追加。

- 実行・監視ランナースクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - プロセス優先度を High に設定するユーティリティを先に呼び出す。
    - `KABUSYS_ENV=paper_trading` の場合は paper-trading 用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離。
    - Broker クライアント生成ファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て、スレッド起動と停止フラグ（data/stop_requested.flag）の検知による安全停止に対応。
    - PID ファイル管理（data/execution.pid）に対応。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - Monitoring は実行環境にかかわらず本番用の `sqlite_path` を使用する設計（運用上の意図的選択）。
    - プロセス優先度設定、監視用 DB 初期化（冪等）、DuckDB 接続の取得、停止フラグによるループ中断、安全なコネクションクローズを実装。
    - `check_once()` 実行時の例外はログとして捕捉し、次ポーリングへ継続。

- 監視 DB 初期化との連携
  - 実行・監視起動時に監視 DB テーブルが存在することを保証する `init_monitoring_db` 呼び出し（src/kabusys/monitoring/* への連携を想定）。

- Paper Trading 検証レポートツール
  - `tools/paper_verification_report.py` を追加。ペーパートレード用 SQLite を読み込み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出して人間向けレポートを標準出力に出力。
  - 判定基準（閾値）を定義し、PASS/FAIL 判定を行う。日付フィルタ (--from / --to) と DB パスの上書きオプションをサポート。

- ポートフォリオ構築ユーティリティ（純粋関数）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点は signal_rank でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコアが 0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が閾値を超える場合、新規候補を除外。unknown セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた投下資金乗数: bull=1.0, neutral=0.7, bear=0.3。他は 1.0 にフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based, equal, score の割当方式を実装。lot_size（単元株）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を反映。残余キャッシュを使った端数処理ロジックを実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `set_process_priority` / `set_cpu_affinity` を追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して互換的に優先度設定を試みる。
    - psutil が提供する定数を getattr で柔軟に参照し、アクセス権や未サポート機能は警告でフォールバック。
    - CPU affinity を最初 N コアに固定する機能（未指定は全コア使用）。不正値は例外。

- リサーチ（ファクター計算）
  - `research/factor_research.py` を追加。DuckDB の prices_daily テーブルを参照して Momentum（1M/3M/6M、MA200乖離）や Volatility（ATR20 等）、流動性指標を算出する関数を実装。計算用のスキャン期間、ウィンドウサイズ等の定数を定義。結果は (date, code) をキーとする dict リストで返却。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Removed
- なし（初回リリース）。

### Security
- .env ファイルには秘匿情報（API トークン等）が記載されるため、生成された `.env` は Git にコミットしない旨を README/テンプレートに明記。
- `config_setup` で秘匿値は表示時にマスクして扱う（画面表示上の配慮）。

### Notes / Migration
- 監視プロセスは MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（環境変数）。不正値は 60 秒にフォールバック。
- Paper trading 時は DB が本番と分離されるため、既存の production DB を上書きしないように `KABUSYS_ENV=paper_trading` を利用してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  設定がない場合は `validate_config` で検出できます。
- `PAPER_FILL_MODE` は "instant" / "partial" / "never" / "reject" のいずれかを指定してください。不正値は起動時に例外となります。
- `set_process_priority` / `set_cpu_affinity` は権限や OS によって動作しない場合があります（その場合は警告が出力されます）。

---
もし特定の変更点やリリースノートの書き方（例えば詳しい Breaking Changes の記述やリリース日付の調整）をご希望であれば教えてください。必要に応じてバージョン履歴を分割して Unreleased セクションを追加することもできます。