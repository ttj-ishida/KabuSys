# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載します。  
このファイルは、現在のコードベースの状態から推測して生成した初期の変更履歴です。

※バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース（コードベースのスナップショットに基づく機能群）。

### Added
- 基本パッケージ情報
  - パッケージ名とバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV = paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを実施。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。実行 PID を data/execution.pid に記録。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の polling ループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番用 sqlite_path を使用する（監視データの一元化）。
    - 停止フラグ検出でループ終了。

- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数 / .env ファイルから設定を読み込むユーティリティ。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env の自動ロード（.env → .env.local、OS 環境変数は保護）を標準で実行。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 複数の設定プロパティを提供（DB パス、J-Quants/Kabu API トークン、Paper Trading の挙動、閾値等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development/paper_trading/live）。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - .env と config/*.yaml の事前検証用 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML がない場合はスキップ）など。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 設定ウィザード（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を新規作成／更新するツール。
    - シークレット項目は入力時/表示時にマスク。
    - .env のテンプレート生成と安全な書き出し処理。

- ログ/プロセスユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name を解決して適切に初期化。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリーンアップを行い二重出力を防止。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収した set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能（環境に依存する操作は失敗時に警告してスキップ）。
    - 権限不足等の失敗時はログ警告で安全にフォールバック。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで上位 N を抽出。
    - calc_equal_weights: 等配分（1/N）。
    - calc_score_weights: スコア加重で重みを計算。全スコアが 0 の場合は等配分にフォールバックし警告を出す。
  - セクター制約・レジーム調整（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター毎エクスポージャーに基づき、新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull=1.0/neutral=0.7/bear=0.3、未知レジームはフォールバックで 1.0）。
  - 株数決定・資金配分（position_sizing）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応。
    - risk_based: 損切り率、許容リスク率に基づく株数算出。
    - equal/score: 重みから割当額を計算し lot_size（単元）に丸め、aggregate cap（available_cash）を超える場合はスケーリングし、残余で lot 単位の再配分も行う。
    - cost_buffer を用いた保守的なコスト見積りに対応。

- リサーチ / ファクター計算（src/kabusys/research/factor_research.py）
  - ファクター計算基盤（DuckDB 経由、prices_daily / raw_financials を参照する設計）。
  - モメンタム指標（1M/3M/6M リターン、MA200 乖離）計算のための定数と calc_momentum の骨子を実装（ターゲット日ベース、データ不足時の None 扱い等）。
  - （注）ファイルの後半はスナップショット上で途中までの実装。DuckDB を使ったファクター計算設計を導入。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - SQLite（デフォルト data/paper_trading.db）を読み、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を計算してレポート出力。
    - 基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づく PASS/FAIL 判定。
    - --from / --to / --db オプション対応。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （なし）

---

補足:
- 設定の自動読み込みや本番/ペーパー用 DB の扱いなど、安全運用に関わる挙動が多数組み込まれています。運用環境（特に KABUSYS_ENV=live）の場合は validate_config による事前チェック、KILL フラグやログ設定の確認を推奨します。
- この CHANGELOG はコード内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。実際のリリース運用時には Git の履歴やリリースノートに基づいて適宜更新してください。