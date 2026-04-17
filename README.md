README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワーク（プロトタイプ）です。本リポジトリには以下の主要コンポーネントが含まれます。

- 発注エンジン（ExecutionEngine）と注文管理（OrderRepository / OrderManager / RiskManager 等）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築ユーティリティ（銘柄選定・重み付け・ポジションサイズ）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- AI 補助モジュール（ニュース NLP によるセンチメント評価 / レジーム判定）
- コマンドラインユーティリティ（.env ウィザード、設定検証、レポート生成 等）

設計上のポイント
- 環境ごとに挙動を切り替え可能（KABUSYS_ENV: development / paper_trading / live）
- Paper Trading は本番 DB と分離（data/paper_trading.db など）
- OpenAI を用いる NLP 処理は API キー必須。失敗時はフェイルセーフで続行する実装
- 監視は SQLite（monitoring.db）にログ永続化。DuckDB は分析用に使用

主な機能
--------
- ExecutionEngine の起動・管理（実発注 / モック発注の切替）
- 定期監視ループ（CPU / メモリ / ディスク / プロセス・データ鮮度など）
- 注文滞留・約定異常の検出とログ化
- リスク監視（ドローダウン・ポジション上限など）と Kill Switch（kill.flag）
- Paper Trading 検証レポート生成（期間指定で稼働率・成功率・レイテンシ等を集計）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）
- ニュースを LLM でスコア化して ai_scores に保存、レジーム判定のための合成ロジック
- .env 対話式ウィザード、起動前の設定検証 CLI

前提条件
--------
- Python 3.9+
- 依存パッケージ（例）:
  - psutil
  - duckdb
  - requests
  - openai（OpenAI SDK、AI 機能を使う場合）
  - PyYAML（設定 YAML の構文検証を行いたい場合）
- .env に必須の環境変数を設定すること（J-Quants / kabu API 等）

セットアップ手順
----------------
1. リポジトリをクローンして依存をインストール
   - 例: python -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt もしくは必要なライブラリを個別にインストール

2. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成/更新します。生成後は必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を確認してください。

3. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにできます

環境変数（主要）
----------------
（.env ファイルに設定する想定。デフォルト値はウィザード / Settings に記載）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う場合必要
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

主な実行方法
-------------
（プロジェクトルートで実行する前提）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に stop flag を作成するとエンジンを停止

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使ってログを残します
  - data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート（標準出力）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite ファイルパス、環境変数 PAPER_TRADING_SQLITE_PATH と併用可）

- AI 関連（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（prices_daily/raw_news 等を含む）を渡して使用します。OPENAI_API_KEY が必要。

停止・Kill スイッチ
-------------------
- ExecutionEngine の停止は以下の方法で行える:
  - 監視コンポーネントが条件を満たした場合、KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 手動停止: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが整然と終了します
- PID ファイル: data/execution.pid（実行中のプロセス ID を保存）を使用して稼働判定を行います

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス（環境変数の読み込み・検証、自動 .env ロード機構）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/...
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, OrderRepository など（発注・管理）

- monitoring/
  - monitoring_db.py — SQLite テーブル定義 + MonitoringDB ラッパ
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各 monitor を束ねる
  - alert_manager.py — LINE 通知（push API ）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（ロット整合・上限調整）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py — forward returns / IC / 統計サマリ

- ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py — ma200 と LLM センチメントを合成して市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- .env は機密情報を含むため Git 管理しないでください（config_setup も警告を表示します）。
- 本番（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知設定を十分に確認してください。
- Paper Trading は本番 DB から完全に分離されるよう設計されていますが、実行前に SQLITE_PATH / PAPER_TRADING_SQLITE_PATH の値とファイルの配置を確認してください。
- OpenAI を呼ぶ機能は API レートや料金の影響を受けます。キー管理・呼び出し頻度に注意してください。
- process priority / cpu affinity の設定は権限や環境により無視される可能性があります（警告ログが出ます）。

開発者向けメモ
----------------
- env 自動読み込み: プロジェクトルートに .env / .env.local があれば自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- DuckDB は分析向けに設計。research モジュールは DuckDB 接続を受け取り SQL で高速に集計します。
- 監視 DB のスキーマは init_monitoring_db() に定義。既存 DB に対する簡単なマイグレーション（カラム追加）も含みます。
- テスト時は OpenAI 呼び出し部分（_call_openai_api など）をモックして外部依存を切る設計になっています。

よく使うコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視プロセス起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
------------------
バグ報告・機能提案は Issue を立ててください。開発に貢献する場合は PR をお願いします。

（以上）