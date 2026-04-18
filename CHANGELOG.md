# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-18

初回リリース。

### 追加
- 基本アプリケーションパッケージを追加（kabusys）。
  - パッケージバージョンは `__version__ = "0.1.0"`。
- 起動スクリプト / CLI を追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 `data/stop_requested.flag` ファイルの存在を検知して行う。
    - 監視用 DB（SQLite）は KABUSYS_ENV に関わらず本番用 `sqlite_path` を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite (`data/paper_trading.db`) を利用して本番 DB と分離。
    - 停止は `data/stop_requested.flag` を検知、PID ファイル（`data/execution.pid`）をサポート。
  - validate_config.py
    - .env や config/*.yaml の起動前検証ツール（CLI）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - PyYAML 非依存で、インストール状況に応じて YAML 検証をスキップ／実行。
  - config_setup.py
    - 対話式 .env 作成／更新ウィザード（CLI）。
    - 必須/任意項目の案内、既存 .env の読み込みとマスク表示、保存前確認など。
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト（期間指定可）。
    - デフォルト DB: `data/paper_trading.db`。環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで上書き可能。
    - 報告指標・閾値（稼働率、注文成功率、送信率、P95 レイテンシ）を出力。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートに基づく `.env` / `.env.local` の読み込み）。
    - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 各種設定取得プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading の各設定など）。
    - `Settings` クラスに `paper_fill_mode`（"instant" | "partial" | "never" | "reject"）等の検証を実装。
- ログ & プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティ `setup_logging()` を提供。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows / POSIX を抽象化したプロセス優先度設定 `set_process_priority()` と CPU affinity 設定 `set_cpu_affinity()` を提供。
    - 権限不足や未対応 OS に対するフォールバック／警告を実装。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates()`、等金額配分 `calc_equal_weights()`、スコア加重 `calc_score_weights()` を実装。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap()`（既存保有のセクターエクスポージャに基づく候補除外）を実装。
    - 市場レジームに応じた乗数 `calc_regime_multiplier()`（"bull"/"neutral"/"bear"）を実装。未知レジームは 1.0 でフォールバック（警告）。
    - コメントで将来の拡張点（価格フォールバック等）を明記。
  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes()` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）丸め、per-position / aggregate 上限、cost_buffer（手数料・スリッページ見積り）の考慮、縮小スケーリングと残差配分ロジックを実装。
- 研究モジュール（実装開始）
  - research/factor_research.py
    - モメンタム・ボラティリティ等のファクター計算を行うモジュールを追加（DuckDB 接続を受け取り prices_daily 等を参照する設計）。（実装途中のファイルあり）
- その他
  - package のエクスポートを整理（kabusys/portfolio/__init__.py で主要関数を公開）。

### 変更
- なし（初回リリースのため該当なし）。

### 修正
- なし（初回リリースのため該当なし）。

### 既知の問題 / 注意点
- apply_sector_cap(): price が欠損（0.0）の場合にエクスポージャが過少見積りされ、セクター制限が期待通りに働かない可能性あり。将来的に前日終値や取得原価でフォールバックする予定（TODO コメントあり）。
- position_sizing: 将来的には銘柄別の lot_size を導入する予定（現状は共通単元 100 を想定、TODO コメントあり）。
- research/factor_research.py はファイル末尾で実装が途中（切れている）。本モジュールはまだ完全ではないため実運用時は注意。
- run_monitoring は監視用 DB 接続に本番 sqlite_path を使用するため、テスト運用時に環境分離が必要な場合は注意。
- 自動 .env ロードはプロジェクトルート検出に依存（.git または pyproject.toml）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

### マイグレーション / 使用上のメモ
- 初期セットアップ手順（推奨）
  1. config_setup.py を実行して .env を作成: python -m kabusys.config_setup
  2. 設定検証: python -m kabusys.validate_config
  3. 実行:
     - 監視: python -m kabusys.run_monitoring
     - 実行エンジン: python -m kabusys.run_execution
  4. Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- ログ出力: デフォルトは logs/<app_name>.log（環境変数 `LOG_DIR` で変更）。標準出力は stdout を使用。
- 環境変数の優先順位: OS 環境 > .env.local > .env。OS 環境変数を保護して .env.local による上書きを許可する設計。

### TODO（今後の改善候補）
- research/factor_research の完全実装（ファクター計算の SQL/ロジック補完）。
- 銘柄毎の lot_size をサポートするための stocks マスタ導入。
- apply_sector_cap における価格フォールバックロジック実装。
- より詳細なテストカバレッジ（特にポジションスケーリングと残差配分の辺り）。
- run_monitoring/run_execution のユニットテスト化（外部依存をモック化）。

---

今後のリリースでは、機能追加・バグ修正・API 互換性の変更をこの CHANGELOG に記録します。問題・要望・バグを見つけた場合は issue を作成してください。