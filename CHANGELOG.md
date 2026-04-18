# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して自動生成されています。実装上の注記や TODO 等も含まれます。

## [Unreleased]

### 注意事項
- 一部モジュールに実装上の TODO/制約コメントがあります（価格フォールバック、銘柄別単元対応、factor_research の未完など）。運用前に該当箇所を確認してください。

---

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージバージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 高機能な .env パーサを追加（export 形式、クォート（エスケープ考慮）、インラインコメント対応）。
  - 環境変数の自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
  - Settings クラスを実装し、アプリケーション設定値（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、環境種別等）を環境変数から取得するインターフェースを提供。
  - Paper Trading 用設定:
    - `PAPER_FILL_MODE`（instant / partial / never / reject）を検証する実装。
    - `PAPER_TRADING_SQLITE_PATH` による専用 DB をサポート。

- CLI / ユーティリティ
  - 環境設定ウィザード: `kabusys.config_setup`（対話式で .env を作成 / 更新）。
  - 設定検証ツール: `kabusys.validate_config`（必須環境変数・パス・YAML ファイル存在等のチェック、--strict オプション）。
  - Paper Trading 検証レポート生成ツール: `kabusys.tools.paper_verification_report`（稼働率 / 注文成功率 / 送信率 / レイテンシ等の集計と PASS/FAIL 判定）。
  - 起動スクリプト:
    - `kabusys.run_monitoring` — SystemMonitor のポーリングループ起動（環境変数 `MONITOR_POLL_INTERVAL` で間隔上書き、停止フラグ対応）。
    - `kabusys.run_execution` — ExecutionEngine 起動スクリプト（`KABUSYS_ENV=paper_trading` 時は Paper DB と MockBroker を利用して本番 DB と分離）。

- 監視・実行基盤
  - 監視用 DB 初期化ユーティリティ `init_monitoring_db` を利用する仕組みを各起動スクリプトに組み込み。
  - run_monitoring:
    - ポーリング間隔の環境変数 `MONITOR_POLL_INTERVAL` を追加（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨の明示。
  - run_execution:
    - Paper Trading と本番の SQLite を明確に分ける（`settings.paper_sqlite_path`）。
    - Engine を別スレッドで実行、停止フラグで安全に停止できる設計。
    - デフォルトの Risk 設定を Engine 起動時に組み立て（max_position_pct, max_utilization, rate limits, circuit breaker, max_drawdown など）。

- ポートフォリオ構築ライブラリ（純関数群）
  - kabusys.portfolio:
    - 候補選定: select_candidates（スコア降順、タイブレークロジックを含む）。
    - 重み計算: calc_equal_weights, calc_score_weights（スコア全ゼロ時は等分配へフォールバックして警告）。
    - セクター制限: apply_sector_cap（既存保有のセクターエクスポージャーに基づき新規候補を除外、"unknown" セクターは上限適用除外）。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" → 1.0/0.7/0.3、未知レジームは 1.0 でフォールバックし警告）。
    - ポジションサイジング: calc_position_sizes
      - risk_based / equal / score の allocation_method をサポート。
      - 単元株（lot_size）で丸め、lot 単位での再配分ロジックを実装。
      - aggregate cap（available_cash）超過時はスケーリングして再配分。
      - cost_buffer による手数料/スリッページ見積りの導入。
      - 設計上の TODO: 将来的に銘柄別単元（lot_size）を stocks マスタで持たせることを想定。

- ユーティリティ
  - ロギングセットアップ: `kabusys.utils.logging_setup.setup_logging`
    - stdout ストリームハンドラ（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログレベル解決順、ログディレクトリ解決順を明示。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作。
    - 標準出力は stdout を利用（stderr ではない点に注記）。
  - プロセス優先度 / CPU affinity ユーティリティ: `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にフォールバック。

- データアクセス
  - DuckDB 接続を前提とした処理を各所で採用（分析用 duckdb）。
  - SQLite（監視・paper_trading）と DuckDB を併用する設計を採用。

- リサーチ（ファクター算出）基盤
  - `kabusys.research.factor_research` の雛形を追加（モメンタム/Value/Volatility/Liquidity の設計、定数、calc_momentum のインターフェース等）。
  - DuckDB を用いた prices_daily / raw_financials 参照での計算方針を明記。
  - （ファイル末尾に未完の実装が見られます。詳細実装は今後の開発対象。）

### Changed
- N/A（初期リリース）

### Fixed
- N/A（初期リリース）

### Security
- 機密情報の扱いに関する注意:
  - `config_setup` にて生成される .env は明示的に Git にコミットしないようコメント。シークレット項目はウィザードでマスク表示。

### Notes / Known issues
- risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる点が TODO コメントとして残っている（将来のフォールバック価格追加を検討）。
- position_sizing: 銘柄別単元対応は TODO（現状は共通 lot_size を仮定）。
- research.factor_research の一部実装が未完（ファイル末尾が途中で切れているように見える）。実運用前に完全実装と検証が必要。
- 一部の外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。環境によりインストールを要する。

---

（この CHANGELOG はコードの内容から推測して作成されています。実際の変更履歴として流用する場合は、コミット履歴やリリースノートと照合してください。）