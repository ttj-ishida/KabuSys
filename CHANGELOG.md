CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
（http://keepachangelog.com/ja/1.0.0/ を参考）

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース: 基本機能群を追加。
- 起動スクリプト
  - run_execution.py: 実際の ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用し MockBrokerClient を利用できるように分離。起動前に停止フラグ (data/stop_requested.flag) をチェックし、PID ファイル (data/execution.pid) を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。停止フラグ検出時や KeyboardInterrupt による安全終了処理を実装。
- 設定周り
  - config.py: .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込みの優先順位は OS 環境変数 > .env.local > .env。読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。Settings クラスを公開し、環境変数の取得・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH 等のデフォルトパスと型変換を提供。
  - config_setup.py: .env の対話式ウィザードを追加。初期作成・更新をガイドする。秘密値（トークン・パスワード）はマスク表示、既存 .env の読み込みと Enter による再利用をサポート。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数の確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース（PyYAML があれば）、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）を実施。--strict オプションで警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。stdout へ StreamHandler、日次ローテート（TimedRotatingFileHandler）でログファイル（logs/<app_name>.log）を出力。ログレベル / ログディレクトリは引数 / 環境変数 / デフォルトの順で解決。既存ハンドラの二重追加を避けるため、再設定時に既存ハンドラをクリアする。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority(level) により "high"/"normal"/"low" を指定可能（Windows の HIGH_PRIORITY_CLASS / nice 値を内部で選択）。set_cpu_affinity で最初の N コアに pin する機能も追加。権限不足や未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等重にフォールバック、警告ログ出力）を実装。
  - portfolio/risk_adjustment.py: apply_sector_cap によりセクター集中上限（max_sector_pct）を超える場合に新規候補を除外するロジックを提供（"unknown" セクターは無視）。calc_regime_multiplier により市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py: position sizing ロジックを追加。allocation_method として "risk_based" / "equal" / "score" をサポート。リスクベースでは risk_pct / stop_loss_pct から株数を計算。単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）と aggregate cap（available_cash）による全体スケーリングを実装。cost_buffer を用いて手数料・スリッページを保守的に見積もる。スケールダウン時は残差（fractional remainder）に基づき lot 単位で再配分する仕組みを持つ。
- 研究用・ツール
  - research/factor_research.py（骨格）: DuckDB の prices_daily/raw_financials を用いたファクター計算の骨格を追加（Momentum, Value, Volatility, Liquidity 指標を計画）。（注）ファイル末尾は未完の実装箇所あり。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（環境変数）または --db オプションで DB を指定。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99.0%、成立率 90% 等）に基づいて PASS/FAIL 判定を行う。P95 計算は独自実装。DB が存在しない場合のエラーメッセージも用意。

Changed
- ログ出力の一元化: 各起動スクリプトは setup_logging を呼び出すよう統一。
- 実行時のプロセス優先度を最初に設定するよう起動スクリプトを調整（set_process_priority("high") を最初に呼び出す）。

Fixed
- .env 読み込みの堅牢化:
  - export KEY=val 形式、クォートされた値（バックスラッシュエスケープ対応）、行内コメントの扱いを実装。
  - .env.local の上書きは OS 環境変数を保護（protected set）して安全に行う。
- 起動スクリプトの DB 接続／終了処理を try/finally で囲み、確実にコネクションをクローズするように改善。
- run_execution の起動時に停止フラグが既に立っている場合は起動しない安全措置を追加。

Security
- .env ファイルを誤ってコミットしないように config_setup.py がヘッダで注意喚起を出力。

Notes / Implementation details
- 既定のパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - Logs: logs/<app_name>.log
- 環境変数の重要項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - PAPER_FILL_MODE（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数。1 未満や不正値はデフォルト 60 秒にフォールバック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると .env 自動読み込みを無効化）
- 実行制御:
  - 停止フラグにより外部から安全に実行ループを終了できる（data/stop_requested.flag）。
  - 起動時に PID ファイルを指定し ExecutionEngine が利用。

未実装 / TODO
- research/factor_research.py の各ファクター計算は一部未完（ファイル末尾に続きあり）。
- 将来的な拡張として銘柄ごとの lot_size 管理（stocks マスタの導入）を想定した TODO コメントあり。
- position_sizing の価格欠損時のフォールバック（前日終値等）の実装は未着手（TODO コメント）。

---

今後のリリースでは、factor 計算の完成、ExecutionEngine / Broker 周りのテストカバレッジ拡充、config のさらに詳細なバリデーション（例: YAML スキーマ検証）などを予定しています。