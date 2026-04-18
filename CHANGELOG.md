# Changelog

すべての変更は Keep a Changelog の形式に従います。  
リリース履歴は後方互換および重要な振る舞いの説明を含みます。

## [0.1.0] - 2026-04-18

初回リリース — 基本的な自動売買フレームワークのコア機能を実装しました。

### 追加
- 実行エントリ / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の存在でループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用パス）を使用して接続。
    - DuckDB との接続確立と監視 DB 初期化（init_monitoring_db）を行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（デフォルト: data/paper_trading.db）して、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの注入。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - 停止フラグの検出で安全にエンジンを停止、PID ファイル管理（data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: 環境変数読み込み・Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env と .env.local を自動読み込み（OS 環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, kill flag 等）。
    - KABUSYS_ENV と LOG_LEVEL の検証、is_live/is_paper/is_dev の判定ヘルパを実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。
    - 標準の設定項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話的に入力・保存。
    - シークレット項目は表示をマスク。
    - .env 書き込みテンプレートを作成（.env を誤ってコミットしないよう注意文を含む）。

- 設定検証
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がインストールされていない場合は警告にフォールバック）。
    - KABUSYS_ENV=live 向けの追加ガード（LINE 通知設定や Kill Switch の設定確認）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL / app_name の解決ロジックを実装。ファイルハンドラ作成に失敗した場合はコンソール出力のみで継続。
    - 既存ハンドラのクリーンアップ（多重設定防止）。
  - utils/process_priority.py:
    - psutil を用いたプロセス優先度設定（"high"|"normal"|"low"）をクロスプラットフォームで実装。Windows と POSIX（Linux/Mac/FreeBSD）に対応。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を追加（権限不足や未対応プラットフォームは警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選抜（同点は signal_rank で決着）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づき新規候補を除外するロジックを実装。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づいて発注株数を決定。lot_size（単元）丸め、1 銘柄上限、aggregate cap による縮小ロジック、cost_buffer を考慮した保守的計算を実装。
    - risk_based では risk_pct / stop_loss_pct を用いたリスクベース算出を実装。
    - aggregate cap の際のスケールダウンと残余キャッシュを用いた端数配分アルゴリズムを実装。

- リサーチ / ツール
  - research/factor_research.py（ファクター計算モジュール）: DuckDB を使用して momentum/value/volatility/liquidity 等のファクターを計算する設計を追加（関数群の骨子を実装）。
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）に基づき PASS/FAIL を判定。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更
- デフォルト・挙動
  - run_monitoring は監視 DB 初期化（init_monitoring_db）と DuckDB 接続を常に行うようにした（環境に依存せず本番 sqlite_path を使用）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB とログを完全分離。
  - .env 読み込みの優先順位を OS 環境 > .env.local > .env と明確化、既存 OS 環境変数は protected として上書きを防止。

### 修正 / 安全策
- .env 読み込みでファイル読み取りに失敗した場合に警告を出し続行するように安全に処理。
- logging_setup: ログディレクトリ作成失敗時にファイル出力をスキップし、stderr/stdout に警告を出すようにして起動不能を回避。
- process_priority/set_cpu_affinity: 権限不足や未対応環境での例外を捕捉して警告にフォールバックするようにした（起動中断を防止）。
- validate_config: PyYAML 未インストール時は YAML 検証をスキップして警告を出すようにした。

### ドキュメント（コード内ドキュメント）
- 各モジュールに docstring と使用例、期待するデフォルト値・環境変数を明記。
- config_setup と validate_config の CLI 使用例を明記。

### 既知の制限 / TODO
- portfolio.position_sizing の価格フォールバック: price が欠損（0）の場合にエクスポージャーが過少見積りされる懸念があり、前日終値や取得原価でのフォールバックが将来の課題として注記。
- research.factor_research.py はファクター計算の骨格を含むが、すべての計算ロジック・テストが完了しているわけではありません（途中まで実装）。
- broker/client 実装や Engine の詳細（ExecutionEngine 内部の挙動）は本変更ログの範囲外。paper_trading 用 MockBrokerClient の振る舞いは設定 PAPER_FILL_MODE に依存（instant/partial/never/reject）。

### 互換性の注意（Breaking Changes）
- 初回公開のため互換性問題はありませんが、以下の点に注意してください:
  - run_monitoring は常に settings.sqlite_path を監視 DB に使用します。環境により別 DB を使いたい場合は設定を上書きしてください。
  - .env 自動読み込みはデフォルトで有効です。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定（例）
- factor_research の完成・テスト追加
- ExecutionEngine / BrokerClient の統合テスト強化
- 各モジュールのユニットテスト追加および CI の整備

もし CHANGELOG の記載内容で補足して欲しい箇所（例えばより詳細な API 使用方法や、特定ファイルの差分に対する説明）があれば指示してください。