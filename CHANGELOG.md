# CHANGELOG

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

デフォルトのリリースバージョンはパッケージの __version__（現在: 0.1.0）に基づいています。以下の記載は、提供されたコードベースの内容から機能追加・挙動を推測してまとめた初期リリース向けの変更履歴です。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-17
初期リリース（推測）。以下の主要機能とユーティリティを提供します。

### 追加
- 全体
  - 初期パッケージ構成を追加。モジュール群: portfolio, execution, monitoring, research, tools, utils, config 周りのユーティリティや CLI を含む。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行 / エンジン
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - 環境に応じて paper_trading 用の専用 SQLite DB を利用（settings.is_paper に基づき分離）。
    - BrokerClientFactory を用いてブローカークライアントを生成（KABUSYS_ENV に応じて Mock/実ブローカーを切替）。
    - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - エンジンは別スレッドで実行され、data/stop_requested.flag による停止検知と grace 停止をサポート。
    - 起動前に監視用テーブルの初期化を行う（init_monitoring_db）。

- 監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを書き込む設計（安全のための想定）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理 / CLI
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml 基準）。
    - .env と .env.local の読み込み優先度（OS 環境変数を保護）。
    - 複数の設定プロパティを提供（DB パス、API トークン、Paper Trading 設定、監視閾値、ログレベル等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py: .env 作成・更新の対話ウィザードを追加。
    - 対話式に主要設定を入力・確認し .env を生成するユーティリティ。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML がない場合はパース検証をスキップ）。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコアが全て 0 の場合は等分配へフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出の実装。
    - 単元株（lot_size）丸め、max_position_pct や max_utilization、cost_buffer を考慮した aggregate cap とスケーリング処理を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度の上限チェック機能（既存保有と売却予定を考慮）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数の算出（未知レジームはフォールバックで 1.0）。

- 研究（ファクター計算）
  - research/factor_research.py
    - DuckDB を用いたファクター計算ユーティリティ（prices_daily / raw_financials テーブルを参照）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率計算（ウィンドウ不足時は None を返す）。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率等の算出（未完の箇所は継続実装の余地あり）。
    - 設計は外部 API 依存を排除し、DuckDB の SQL と Python 組合せで完結。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの算出と PASS/FAIL 判定（閾値はソース内定義で変更可能）。
    - --from / --to / --db オプション、環境変数 PAPER_TRADING_SQLITE_PATH による DB 指定に対応。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収（psutil を利用）。
    - CPU affinity の設定ヘルパ（set_cpu_affinity）を提供。
    - 権限不足や未対応 OS の場合は警告を出し安全にスキップ。

### 変更
- なし（初期リリースとして新規追加が主体）。

### 修正
- なし（初期リリースとして新規追加が主体）。

### 既知の制約 / 注意事項
- .env の自動ロードはプロジェクトルートが検出できない場合スキップされる。
- PAPER_TRADING 用 DB は本番 DB と意図的に分離される（paper_trading モード時）。
- process_priority / cpu_affinity の操作は OS 権限や psutil の実装に依存し、失敗時は警告ログで済ませる設計。
- portfolio.position_sizing の一部（価格欠損時のフォールバック等）は TODO コメントが残されており、将来的な拡張が想定されている。
- research.calc_volatility の SQL 部分がファイル末尾で途中 (コメントや文字列切れ) の可能性があるため、完全実装は要確認。

---

開発・運用上の重要な設定例や操作手順は README やドキュメントにまとめることを推奨します。必要であれば、この CHANGELOG をベースにリリースノート（英語/日本語）やリリース手順のドラフトも作成します。