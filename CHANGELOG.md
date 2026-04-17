CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" 準拠の形式で作成しています。  
コードベースの内容から推測して記載しています（実装ファイル名・関数名を参照）。

Unreleased
----------
- Added
  - ニュースNLP（OpenAI を用いたニュースセンチメントスコアリング）の導入を開始（kabusys/ai/news_nlp.py）。
    - タイムウィンドウ計算、バッチ送信（最大20銘柄）、レスポンス検証、スコアの ±1.0 クリップ、エクスポネンシャルバックオフ／リトライ方針を導入。
    - JSON Mode を期待するシステムプロンプト設計。APIキーは引数または環境変数 OPENAI_API_KEY で指定。
  - 研究・ファクター計算機能の拡張（kabusys/research/*）。
    - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 接続を受け取る純粋関数群）。
    - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリを追加。
  - ポートフォリオ構築・リスク制御機能を追加（kabusys/portfolio/*）。
    - 候補選定、等金額／スコア配分、セクター上限適用、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap スケールダウン）。
  - 実行系・監視起動スクリプトの追加（src/kabusys/run_execution.py、src/kabusys/run_monitoring.py）。
    - プロセス優先度設定（高優先）を起動時に適用。
    - 停止フラグ・PID ファイルによるプロセス制御に対応。
  - Paper Trading 向け検証レポート CLI ツールを追加（kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を期間指定で出力し、閾値判定（PASS/FAIL）を行う。

- Changed
  - 環境設定読み込みの自動化と堅牢化（kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動でロード。
    - .env のパースが強化され、export プレフィックス、クォートされた値、インラインコメント処理に対応。
    - OS 環境変数は保護され、.env.local は上書き優先で読み込まれる。
  - DB に DuckDB を採用（research/ai 等での分析処理に使用）。デフォルトパスは DUCKDB_PATH 環境変数で指定可能。
  - 実行エンジンと監視は DB 接続の分離を導入。
    - run_execution: KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - run_monitoring: 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。
  - process_priority ユーティリティ（kabusys/utils/process_priority.py）で Windows と POSIX の差を吸収し、CPU affinity 設定関数を追加。

- Fixed
  - MONITOR_POLL_INTERVAL の解釈で 0 以下や不正値入力時にデフォルトへフォールバックするように改善（run_monitoring.py）。
  - PAPER_FILL_MODE の入力検証を追加（Settings.paper_fill_mode）。無効値で ValueError を送出するように変更。
  - calc_score_weights が全スコア 0 の場合に等金額配分へフォールバックするように警告を追加（kabusys/portfolio/portfolio_builder.py）。
  - apply_sector_cap の既存保有エクスポージャ計算で売却予定銘柄除外の対応と unknown セクターの扱いを明確化（kabusys/portfolio/risk_adjustment.py）。
  - calc_position_sizes の aggregate cap スケールダウン時に端数分を lot_size 単位で再配分するロジックを導入し、保守的にコストバッファ（cost_buffer）を考慮（kabusys/portfolio/position_sizing.py）。
  - research/feature_exploration.rank にて浮動小数の丸めによる ties 検出漏れを防ぐ丸め処理を追加。
  - calc_forward_returns の horizon 入力検証を追加（正の整数かつ上限 252 日）。

- Security
  - 必須の外部 API トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は Settings 経由で必須チェックを行うように。未設定時は ValueError を送出し明示化。

- Documentation / CLI
  - 各モジュールに docstring と設計メモを充実（ファイル先頭や各関数に使用例・注意書き）。
  - tools.paper_verification_report に CLI 引数（--from, --to, --db）を追加。

0.1.0 - 2026-04-17
------------------
初回リリース想定（コードベースの現状をまとめたリリース相当）。

- Added
  - コア機能
    - 自動売買システムの基本モジュール群を追加（kabusys パッケージ）。
    - 実行エンジン / 注文管理 / リスク管理 / リコンシリエータなどの実行系骨組み（参照: run_execution.py、execution/*）。
    - 監視 SystemMonitor のポーリング起動スクリプト（run_monitoring.py）と監視 DB 初期化処理。
  - データ処理・研究機能
    - DuckDB ベースのファクター計算モジュール（momentum/volatility/value）。
    - 特徴量探索・IC・統計サマリ機能。
  - ポートフォリオ管理
    - 候補選定、重み付け（等金額・スコア）、ポジションサイズ計算、セクター制約、レジーム乗数。
  - ユーティリティ
    - .env パースと自動ロード（環境保護あり）。
    - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）。
  - ツール
    - Paper Trading 用検証レポート生成スクリプト（CLI）。

- Changed
  - SQLite / DuckDB のデフォルトパスと接続方針を定義（Settings）。
  - 実行時ログレベル設定（Settings.log_level）の検証を追加。
  - KABUSYS_ENV の許容値を厳格化（development / paper_trading / live）。

- Fixed
  - 各種境界ケース（欠損データ、ゼロ除算、データ不足）に対する安全処理を多数追加。
  - run scripts の停止フラグ処理と PID 管理の堅牢化。

アップグレード／移行に関する注意
------------------------------
- 環境変数の自動ロード
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。OS 環境変数は上書きされません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等は Settings によって必須扱いになっています。未設定だと起動時に ValueError が発生します。
- Paper Trading
  - paper_trading 用 DB を使う場合、PAPER_TRADING_SQLITE_PATH を設定するかデフォルト data/paper_trading.db を用いてください。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用し、本番 DB と分離します。
- OpenAI（ニュースNLP）
  - news_nlp を使用するには OPENAI_API_KEY を環境変数または関数引数で指定する必要があります。
  - API 利用は課金・レート制限・データ取り扱いに注意して運用してください。
- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。1 秒未満や非数値は無効と判断されデフォルト 60 秒にフォールバックします。

既知の制限 / TODO
-----------------
- news_nlp の score_news は大きな処理フローを実装済みですが、部分的に追加検証やエラーハンドリングの微調整が必要な箇所があります（現在も改善・テスト継続中）。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応へ拡張予定。
- apply_sector_cap の価格欠損時のフォールバック（前日終値等）は将来的に追加検討予定。

その他
-----
- 各モジュールに詳細な docstring が付けられており、実装方針・設計ノートが参照可能です。必要に応じて関数注釈や例外挙動を確認してください。