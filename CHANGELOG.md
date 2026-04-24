CHANGELOG
=========

全般
----
- 本ドキュメントは Keep a Changelog 準拠の形式で、リポジトリの変更・追加点をコードベースから推測してまとめたものです。
- バージョンはパッケージ定義 (kabusys.__version__) に合わせて 0.1.0 としています。

0.1.0 - 2026-04-24
-----------------

Added
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを実装。KABUSYS_ENV が paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。停止フラグ (data/stop_requested.flag) と PID ファイル管理に対応。スレッドでエンジンを起動し、停止フラグ検出時は安全に停止するロジックを収容。
  - run_monitoring.py: SystemMonitor ポーリングループの起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用。停止フラグ検知でループを終了。

- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。シークレットをマスク表示、選択肢・デフォルト提示、保存前確認、.env に注意書きのヘッダを付与して出力。
  - validate_config.py: .env と config/*.yaml の設定を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パース検証（PyYAML が無い場合は警告）。--strict モードで警告を FAIL 扱いにできる。

- 設定読み込み・管理を強化
  - config.py: プロジェクトルートを .git または pyproject.toml で自動検出し、.env/.env.local を自動ロードする仕組みを実装（OS 環境変数を保護して上書き制御）。.env パーサは export 形式、クォートされた値とエスケープ処理、インラインコメントの扱いなどをサポート。Settings クラスを提供し、各種設定値（DB パス、LINE トークン、KABUSYS_ENV 判定、paper_trading 用設定、監視閾値など）をプロパティで取得可能にした。PAPER_FILL_MODE の妥当性検証も追加。

- ポートフォリオ構築・リスク管理用純関数群を追加
  - portfolio/portfolio_builder.py: BUY シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を実装。スコアが全て 0 の場合のフォールバックに対応。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。unknown セクターの扱いや未知レジームのフォールバックを明記。
  - portfolio/position_sizing.py: 発注株数計算 (calc_position_sizes) を実装。allocation_method として "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ想定）を考慮した丸め・再配分ロジック（fractional remainder に基づく追加配分）を実装。

- ログ・プロセス管理ユーティリティを追加
  - utils/logging_setup.py: 全起動スクリプト共通のログ設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラの二重登録防止、LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定を実装。Windows/Linux/macOS 等を抽象化して呼び出し側がプラットフォームを意識しないようにし、アクセス権限不足や未対応 OS の場合は警告でスキップする。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。注文成功率（fill/send）、システム稼働率、P95 レイテンシなどを集計し PASS/FAIL 判定を出力。期間指定や DB パス指定の CLI オプションを提供。P95 の計算、各テーブルの存在チェック時のフォールバックを考慮。

- research/factor_research.py（骨組み）
  - ファクター（モメンタム、バリュー、ボラティリティ、流動性）計算モジュールの骨組みと定数を追加。DuckDB 接続を用いて prices_daily / raw_financials を参照する設計方針を記載（実装途中と思われる箇所あり）。

Changed
- パッケージ初期バージョンとしてモジュール群を整理し、kabusys.__init__.py に __version__ = "0.1.0" を設定。

Fixed
- なし（初期リリース相当。コード内に複数の堅牢化・保護ロジックが導入されているため、実装上の注意点を WARN/例外で扱う設計になっている）。

Security
- .env ファイルの取り扱いに関する注意書きを config_setup.py の出力に追加し、.env を Git にコミットしないよう明示。

Notes / Implementation details（推測）
- 起動スクリプトはプロセス優先度を最初に "high" に設定する挙動になっており、ミッションクリティカルなリアルタイム性を重視している。
- run_execution は BrokerClientFactory を用いて実際のブローカークライアント or モックを選択する設計で、paper_trading と live を明確に分離している。
- 監視 (monitoring) は本番用の SQLite を常に参照する仕様になっているため、monitoring データの一貫性確保に注意が必要。
- ロギングは stdout とファイルへ同時出力し、ログディレクトリ作成失敗時もサービス継続できる設計になっている。
- position_sizing の aggregate スケーリングは丸め単位（lot_size）を考慮した再配分を行うため、小数切捨てによる不利なスケーリングを緩和する工夫がある。

今後の改善候補（提案）
- research/factor_research.py の未完成部分（末尾）を実装してユニットテストを追加する。
- position_sizing の lot_size を銘柄ごとに設定できるように拡張する（TODO 記載あり）。
- .env パーサのエッジケースを増やすテストを追加（複雑なクォート・エスケープケース等）。
- 実行環境での権限不足や psutil の未サポート環境に対する CI/テストの整備。
- DB 接続の抽象化や接続プール検討（特に長時間稼働する monitoring/engine コンポーネント向け）。

ライセンス、貢献、著者情報等はリポジトリ内の該当ファイルを参照してください。