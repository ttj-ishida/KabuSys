# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

全般的注意
- 日付はこの CHANGELOG 作成日（2026-04-19）をリリース日として採用しています（コード内のコメントやサンプル日付を踏まえた推定）。
- 環境変数やファイルパスのデフォルト設定、コマンドラインの使い方等は各モジュールの docstring / コメントを基に要約しています。

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - Settings クラス (`src/kabusys/config.py`) を追加。
    - 環境変数経由での設定取得を一元化（J-Quants / kabuステーション / DBパス / ログレベル等）。
    - `.env` 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
    - `paper_sqlite_path`, `paper_fill_mode` など Paper Trading 向け設定をサポート。
    - 環境名検証 (`KABUSYS_ENV`: development|paper_trading|live) や `LOG_LEVEL` の検証を実装。

- 環境設定ウィザード CLI
  - `src/kabusys/config_setup.py` を追加。
    - 対話式に `.env` を生成・更新するウィザード。
    - J-Quants / kabu API / DB パス / LINE 通知設定など主要項目をサポート。
    - 既存 `.env` の読み込み、マスク表示、確認プロンプト、ファイル書き出し機能を実装。
    - 実行方法: `python -m kabusys.config_setup`（`--env-file` オプションあり）。

- 設定検証 CLI
  - `src/kabusys/validate_config.py` を追加。
    - 起動前に必須環境変数やパス、config/*.yaml の存在・パース等を検証。
    - PyYAML が無ければ YAML 検証をスキップして警告を出力。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 実行方法: `python -m kabusys.validate_config`。

- 起動スクリプト（プロセス）
  - モニタリング用起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - SystemMonitor のポーリングループを起動。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0 以下や不正値はデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグファイル (`data/stop_requested.flag`) を検知してループを終了。
    - プロセス優先度を起動時に "high" に設定。
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py` を追加。
    - ExecutionEngine を組み立て・起動するエントリポイント。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）に記録して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を初期化。
    - ExecutionEngine はデーモンスレッドで run_session を実行し、停止フラグによる停止処理・PIDファイル扱いを実装。
    - プロセス優先度を起動時に "high" に設定。

- 監視 DB 初期化 / DB 接続サポート
  - `init_monitoring_db` を利用して監視テーブルの確保を行う（Monitoring 起動・Execution 起動時に冪等に呼ぶ実装）。

- DuckDB サポート
  - DuckDB 接続を各種処理（ExecutionEngine、research 等）で利用するため `duckdb` 接続を初期化して渡す実装を追加。

- ロギングユーティリティ
  - `src/kabusys/utils/logging_setup.py` を追加。
    - ルートロガーに StreamHandler（stdout 出力）と TimedRotatingFileHandler（アプリ別ログファイル、日次ローテーション）を設定。
    - ログディレクトリの解決順と作成処理、既存ハンドラのクリア、出力レベルの解決ロジックを実装。
    - ファイル出力に失敗した場合はコンソール出力のみで継続。
    - stdout を使うことで cron 等のリダイレクトを想定。

- プロセス優先度 / CPU affinity ユーティリティ
  - `src/kabusys/utils/process_priority.py` を追加。
    - Windows / POSIX(Linux, macOS 等) の差を吸収してプロセス優先度（high|normal|low）を設定。
    - CPU affinity 固定機能（最初の N コアに固定）を実装。
    - psutil を利用、権限不足や未実装時は警告でスキップする堅牢性を備える。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/` 以下を追加。
    - portfolio_builder: 候補選定 select_candidates、等金額/スコア重み calc_equal_weights / calc_score_weights（スコア全0時のフォールバック警告を実装）。
    - risk_adjustment: セクター集中制限 apply_sector_cap（売却予定銘柄の除外、"unknown" セクターは適用除外）および市場レジーム乗数 calc_regime_multiplier（bull/neutral/bear に対する乗数、未知値は警告と1.0フォールバック）。
    - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、lot_size（単元）で丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全弁、残差に基づく追加配分アルゴリズム）。
    - これらは DB 非依存の純粋関数でメモリ内計算のみを行う設計。

- Paper Trading 検証レポート
  - `src/kabusys/tools/paper_verification_report.py` を追加。
    - Paper Trading の SQLite ログから各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - `--from`, `--to`, `--db` オプションを備える。環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パス指定可能。
    - データがない場合の N/A ハンドリングや sqlite の OperationalError をキャッチしてフォールバック。

- 研究用ファクター計算（下地）
  - `src/kabusys/research/factor_research.py` を追加（モメンタム / MA200 / ATR / ボリューム等の計算方針と定数定義）。DuckDB 経由で prices_daily / raw_financials を参照する設計。
  - 実装は未完部分がある（コード断片あり）が、設計と定数、関数インターフェースが準備済み。

- パッケージ公開用 __all__ とモジュール初期化
  - portfolio パッケージのエクスポート一覧を定義し、主要関数をトップレベルからインポート可能にした。

### Changed
- ロギングの既定動作
  - コンソール出力を stderr ではなく stdout にする方針を採用（cron/task scheduler でのリダイレクトを考慮）。

### Fixed
- （初期リリースにおける設計上の注意点・堅牢化）
  - 環境変数パースの強化: `.env` ファイルのパースでクォートやエスケープ、インラインコメント処理を細かく扱うように実装。
  - 環境変数の自動ロードで OS 環境変数を保護する仕組み（protected set）を追加し、既存の OS 環境変数を意図せず上書きしないようにした。

### Security
- 特になし（初期実装）

---

今後追記する可能性のある項目（想定）
- factor_research の完全実装（モメンタム等の SQL/数値処理）。
- ExecutionEngine / SystemMonitor 内部の詳細な監査ログやメトリクス出力（duckdb / monitoring テーブルの充実）。
- 単体テスト・CI 設定に関する変更履歴。

（以上）