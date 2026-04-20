KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための軽量な Python コードベースです。主要機能は次の通りです。

- Execution Engine: ブローカークライアント経由での発注・リスク管理・注文再照合
- Monitoring: システム状態・注文状況・リスク（ドローダウン等）を定期チェックしてアラート／Kill Switch 発動
- Research: DuckDB を用いたファクター計算・特徴量分析（モメンタム、ボラティリティ、バリュー等）
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- AI 補助機能: ニュースの LLM によるセンチメントスコアリング、レジーム判定（OpenAI）
- ツール: ペーパートレード検証レポート生成スクリプト 等
- ユーティリティ: 設定ウィザード、設定検証、統一的なログ設定、プロセス優先度設定

主な特徴
-------
- 設定は .env ファイル（または環境変数）で管理。config_setup.py による対話式ウィザードを提供
- paper_trading 環境では発注はモック化され、paper 用の SQLite DB に完全分離して記録
- DuckDB をデータ分析用に利用（prices_daily / raw_financials 等）
- ログはコンソール + 日次ローテートファイルに統一
- Kill Switch（data/kill.flag）で全自動停止できる安全設計
- LLM（OpenAI）と連携してニュースセンチメントや市場レジームを算出（API キー必要）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing に | 演算子を使用）
- システム Python 仮想環境を利用することを推奨

依存パッケージ（主要）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML （config YAML の検証を行う場合）
- その他ピンポイントの依存がある場合はプロジェクト側の requirements.txt を参照してください

例（仮想環境作成・依存インストール）
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai pyyaml

初期設定 (.env)
1. 対話式ウィザードで .env を生成:
   - python -m kabusys.config_setup
   - 対話で必須項目（J-Quants トークン、kabu API パスワード等）を入力してください
2. 生成した .env を確認後、設定検証:
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告も fail 扱いになります

データディレクトリ
- デフォルトでは data/ に DB や PID/flag ファイルを作成します。権限やパスを確認してください。
- ログディレクトリはデフォルト logs/ （環境変数 LOG_DIR で変更可）

重要な環境変数
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- OPENAI_API_KEY（AI 機能を利用する場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。run_monitoring 起動時に環境変数で上書き可）
- PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）

使い方（実行例）
---------------

監視プロセスの起動
- デフォルトポーリング 60 秒（MONITOR_POLL_INTERVAL で変更可能）
- python -m kabusys.run_monitoring
- 実行中、プロジェクトルート/data/stop_requested.flag が存在するとループを抜けて終了します
- 監視は常に本番用 sqlite_path（settings.sqlite_path）を使用します（環境に依存しません）

Execution Engine（発注エンジン）の起動
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録する
- python -m kabusys.run_execution
- 起動時に data/stop_requested.flag が既にある場合は起動せず終了します
- エンジンは data/execution.pid（デフォルト）に pid を書きます。停止は stop flag を置くか Kill Switch（kill.flag）で行います

設定ウィザード / 検証
- .env を生成・編集: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを --db で指定するか環境変数 PAPER_TRADING_SQLITE_PATH を設定してください

AI 関連（ニュース NLP / レジーム判定）
- ライブラリ関数として利用可（OpenAI API キー必須）
  例（REPL など）:
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.ai.news_nlp import score_news
    score_news(conn, date(2026, 4, 1), api_key="sk-...")

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 4, 1), api_key="sk-...")

- API 呼び出し失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計

停止・Kill Switch
- ExecutionEngine を安全に停止するには以下を使用:
  - KillSwitch: 監視モジュールが条件（ドローダウン超過等）に応じて data/kill.flag を書き込む
  - 手動停止: data/stop_requested.flag を置くと run_execution/run_monitoring はループを抜けて終了します
- kill.flag を手動で消すには: rm data/kill.flag
- Settings による起動時の自動クリア設定 KILL_FLAG_CLEAR_ON_START=1 を利用できますが、本番では 0 推奨

ログ
----
- 共通ロガー設定: kabusys.utils.logging_setup.setup_logging を各エントリポイントで呼び出しています
- デフォルトは logs/<app_name>.log（日次ローテート、30日保持）+ stdout 出力
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で指定可能

ディレクトリ構成（抜粋）
-----------------------

プロジェクトの主要なモジュールとファイルは次の通りです（src/kabusys 以下）:

- __init__.py
- config.py
  - Settings クラス: 環境変数の解決・検証ロジック
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI（--strict オプションあり）

- run_execution.py
  - ExecutionEngine を起動するスクリプト。paper_trading での挙動切替あり

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔指定可能

- monitoring/
  - monitoring_db.py: SQLite のスキーマ初期化とCRUD（MonitoringDB クラス）
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - risk_monitor.py: ドローダウン／ポジション上限の監視
  - kill_switch.py: kill.flag の書き込み/管理
  - trade_monitor.py: 注文滞留や約定異常検出（参照されます）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution ロジックやブローカー抽象化（ファクトリ経由で Mock/実ブローカーを選択）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・キャップ適用
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー等の計算（DuckDB ベース）
  - feature_exploration.py: 将来リターン計算・IC（Information Coefficient）等

- ai/
  - news_nlp.py: ニュースをまとめて LLM に問い合わせ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py: ETF(1321) の MA200 乖離とマクロニュース LLM を合成しレジーム判定
  - どちらも OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）

- tools/
  - paper_verification_report.py: Paper Trading の運用検証レポート生成スクリプト

- utils/
  - logging_setup.py: ログの統一設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config が本番チェックをアシストします。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。誤って本番 DB を上書きしないよう .env を確認してください。
- OpenAI 呼び出しは課金・レート制限があります。API キー管理と呼び出し頻度に注意してください。
- DuckDB / SQLite はファイルベース DB です。バックアップと整合性に留意してください。

開発・テスト
------------
- 各モジュールはライブラリとしてインポートして単体テストしやすい純粋関数が多く設計されています（特に portfolio / research）。
- run_monitoring.run_once 相当のモードは MonitoringEngine.run_once を使ってテスト可能です。
- External API 呼び出し部分（OpenAI / ブローカー）は差し替え（モック）ができるよう設計されています。unit test では patch を活用してください。

ライセンス・貢献
----------------
- （本 README にライセンス記載がないため、リポジトリの LICENSE を参照してください）
- バグ報告・機能提案は issue を作成してください。コントリビューションは歓迎します。

付録: よく使うコマンドまとめ
--------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI ニューススコア（コードから）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, date(2026,4,1))

この README はコードベースの主要機能・運用フローを簡潔にまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。