# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づいています。

## [Unreleased]
- なし

## [0.1.0] - 初回リリース
初期リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、レポートツールなどを含みます。

### 追加
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60秒）。
    - 停止用フラグファイル data/stop_requested.flag の検出で安全にループ停止。
    - 監視は環境変数 KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - Engine をデーモンスレッドで実行し、停止フラグで停止可能。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを管理。

- 設定管理
  - config.py
    - 環境変数の読み込み・ラッパー Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）経由で .env/.env.local を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - 自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env の行パースで export 形式、クォート・エスケープ、インラインコメントを考慮した堅牢な実装を提供。
    - 必須設定取得用の _require()、各種パス・閾値・フラグ等を Settings のプロパティとして提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, 各種閾値など）。
    - 環境 (development/paper_trading/live) とログレベルの検証。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - J-Quants/Kabu API トークン等を秘匿入力対応（表示はマスク）。
    - デフォルト値、選択肢、説明文を含む対話式入力。保存前に確認ダンプを表示。
    - .env 書き込み時にヘッダコメントを付与し、Git にコミットしない注意喚起を含む。

  - validate_config.py
    - CLI で .env および config/*.yaml の設定・存在検証を行うツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML 未インストール時はスキップして警告）などを実施。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング/プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を定義。
  - utils/process_priority.py
    - Windows と POSIX を吸収するプロセス優先度設定ユーティリティを追加。
    - CPU affinity 設定関数を提供（指定コア数でプロセスをピン留め）。
    - 権限不足などのエラーは警告ログに留めて安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・同点は signal_rank でブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額フォールバックと警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を基に新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく発注株数算出を実装。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケールダウンと残差処理を実装。
    - cost_buffer を用いた保守的なコスト見積りをサポート。

- 研究/ファクター計算
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum/Value/Volatility/Liquidity を想定）。
    - calc_momentum のインターフェースを含む（DuckDB 接続を受け取り prices_daily を参照してモメンタム指標を算出する設計）。注: モジュールは設計に従った実装を進めるためのベースを提供。

- ツール類
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH / --db で対象 DB を指定可能。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - P95 計算、期間フィルタ、閾値に基づく PASS/FAIL 判定を実装（閾値はソースコード内定義: 稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。

- パッケージ初期設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - portfolio 等の公開 API を __all__ で整理。

### 変更
- 既存の設計方針/仕様を明確化
  - .env の自動ロードはプロジェクトルートの検出に基づき、CWD に依存しない実装になっている点を明記。
  - logging_setup は stdout を用いることでタスクスケジューラ / cron でのログ取り回しを想定。

### 修正（バグ修正・堅牢化）
- 環境変数パース処理の堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などを正しく処理するよう改良。
- run_monitoring/run_execution の安全停止処理
  - stop flag ファイル検出時の明示的ログ出力と後片付け（DB 接続クローズ）を保証。
- ログハンドラ重複防止
  - setup_logging が既存ハンドラを flush/close してから再設定することで二重出力を防止。
- process_priority の権限エラーや未サポート OS へのフォールバックを警告ログに変更して起動継続を確保。

### セキュリティ / 注意点
- .env の生成スクリプトは .env を平文で書き出します。README/運用手順に従い .env を絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- 設定検証ツールは PyYAML 未インストール時に YAML 検証をスキップして警告を出します。YAML 検証が必要な場合は PyYAML をインストールしてください。

---

この CHANGELOG は、リポジトリ内のソースコード構造とコメントから推測して作成しています。実際のコミット履歴・チケット等に基づく正式な変更履歴は適宜補完してください。