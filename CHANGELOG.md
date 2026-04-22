# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています（日本語訳）。

最新の変更は一番上に表示します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-22
最初の公開リリース。以下の主要機能・CLI・ユーティリティを含みます。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - モジュール構成: data / strategy / execution / monitoring 等の名前空間をエクスポート。

- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。
    - BrokerClientFactory によるブローカークライアント生成（KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading 用 DB に分離）。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動（スレッド実行）。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理（data/execution.pid）。
    - DuckDB と SQLite の接続確立（paper_trading は専用 SQLite を使用）。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視用 DB（SQLite）接続と duckdb 接続の初期化。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計注記あり。
    - 停止フラグ検出でループ終了、KeyboardInterrupt の取り扱い。

- 設定管理・検証
  - config.Settings クラス:
    - 環境変数の取得ラッパー（必須チェック、型変換、デフォルト値）。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のパスプロパティ、env 判定（development/paper_trading/live）、ログレベル検証、paper_fill_mode の入力検証等を提供。
    - settings インスタンスをモジュールレベルでエクスポート。

  - .env 自動読み込み:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。

  - config_setup: 対話式ウィザードで .env の初期作成・更新を支援。
    - 対話プロンプト、既存値の再利用、secret 項目のマスク表示、保存確認。
    - .env 書き出しテンプレート (注意: .env を Git にコミットしない旨を明記)。

  - validate_config: 起動前チェック CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリチェック。
    - config/*.yaml 存在確認および PyYAML があればパース検証（PyYAML 未インストール時は警告）。
    - --strict フラグで警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理。
    - コンソール出力は stdout を使用（cron 等での取り扱いを意図）。

  - utils.process_priority:
    - psutil を用いてプラットフォームを吸収したプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 固定機能。
    - Windows/Linux/macOS (一部 POSIX) をサポートし、権限不足等で失敗した場合は警告ログでスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトフォールバックあり）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算。
    - 単元 (lot_size) 丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。

- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）からデータを集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ (avg/max/P95) / リスク却下数 を算出してレポート出力。
    - P95 計算、期間フィルタ（--from / --to）、閾値に基づく PASS/FAIL 判定を実装。

- 研究・ファクター計算（下地）
  - research.factor_research: DuckDB 接続を受け、Momentum/Value/Volatility/Liquidity 等のファクター計算を行う設計。モメンタム計算関数の雛形を含む（詳細実装は継続）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 設計上の挙動
- run_monitoring は意図的に KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨のコメントがある（監視データを本番 DB に残す設計）。運用時は注意。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の安全策）。
- logging_setup はログディレクトリ作成に失敗した場合、ファイルハンドラの作成をスキップして標準出力のみで動作する。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム依存で失敗する場合があるが、例外は捕捉して警告する。

### 既知の TODO / 制約
- portfolio.position_sizing:
  - 銘柄別 lot_size の将来的拡張（現在は全銘柄共通の lot_size）。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値などのフォールバック実装を検討中（TODO コメントあり）。
- research.factor_research: ファイル末尾が未完（実装途中）。ファクター計算の完全実装は今後の作業。
- 一部の機能は外部ライブラリ依存（psutil, duckdb, PyYAML）。環境によりインストールが必要。

### セキュリティ
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup のヘッダに明記）。

---

参照: Keep a Changelog — https://keepachangelog.com/（英語）