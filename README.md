KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の軽量実装です。本リポジトリは以下の主要領域で構成されています。

- Execution: 注文発行・リスク管理・注文リコンシリエーションを行う ExecutionEngine
- Monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch（停止フラグ）
- Portfolio: 銘柄選定・重み計算・ポジションサイズ計算・セクター制約など
- Research: ファクター計算（モメンタム／バリュー／ボラティリティ）、特徴量探索（IC等）
- AI: ニュースの NLP によるセンチメント、レジーム判定（OpenAI を利用）
- Tools: ペーパートレードの検証レポート生成 等
- Utils: ロギング設定・プロセス優先度設定 等

機能一覧
--------
主な機能（抜粋）:

- Execution
  - 実注文（live）およびペーパートレード（paper_trading）に対応
  - BrokerClientFactory による実/モックブローカー切替
  - リスク管理（max position、drawdown、rate limits など）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・Execution プロセスの死活・データ鮮度監視
  - TradeMonitor：注文滞留・約定異常などの検出（trade_logs）
  - RiskMonitor：ドローダウン／ポジション上限のチェックと risk_logs への記録
  - KillSwitch：閾値超過時に data/kill.flag を書き込むことで Execution を停止
  - MonitoringEngine：複数モニタの定期実行とアラート管理
- Portfolio
  - 候補選定（スコア順）、等金額／スコア加重配分、リスクベースのポジションサイズ
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（mom/vol/value）と forward return / IC 計算
- AI
  - OpenAI API を用いたニュースセンチメントスコア（ai_scores）と市場レジーム判定
  - API 呼び出しのリトライ・レスポンス検証・部分書き込み設計（冪等性）
- Tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- Utilities
  - 統一的なログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

セットアップ手順
----------------

前提
- Python 3.9+ を推奨（duckdb, psutil 等が必要）
- システムにより追加パッケージが必要: duckdb, psutil, openai（AI 機能利用時）、PyYAML（config 検証時に必須ではないが有ると YAML の検証を行う）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai

   ※ requirements.txt がない場合は上記パッケージを個別にインストールしてください。開発用に PyYAML を入れると config の YAML 検証が有効になります:
   - pip install pyyaml

3. プロジェクトルートに data/ と logs/ を作成（通常はコードが自動作成しますが手動でも可）
   - mkdir -p data logs

4. .env の生成（対話式ウィザード）
   - python -m kabusys.config_setup
     - J-Quants / kabu API のトークンやパスワードなどの必須値を入力します。
   - 生成された .env は絶対にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（よく使うもの）:
  - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
  - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH （監視 DB: デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH （paper_trading 用 DB: data/paper_trading.db）
  - LOG_LEVEL (DEBUG/INFO/...)
  - OPENAI_API_KEY（AI 機能を使う場合に必須）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

使い方
------

起動スクリプト（モジュール実行）:
- ExecutionEngine（実行エンジン）起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db に書き込みます。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書き込みます（設定でパス変更可）。
- Monitoring（ポーリング監視）起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でループ間隔を上書き可能（秒、デフォルト 60）。
    - 常に本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録します。
    - 停止は data/stop_requested.flag を作成することで行えます。

ツール:
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可。環境変数 PAPER_TRADING_SQLITE_PATH も参照。

AI 機能:
- ニュース NLP / レジーム判定 は OpenAI API（OPENAI_API_KEY）を必要とします。
- OpenAI API のレスポンスは検証され、失敗時はフェイルセーフ挙動（0.0 など）で進みます。

停止・Kill Switch:
- KillSwitch は監視で閾値（ドローダウン等）を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこれを検知して安全停止します。
- 手動停止は data/stop_requested.flag を作成するか（run scripts がこれを見て終了）、execution.pid を参照してプロセスを終了してください。

設定・データパス挙動（要点）
- Settings クラスで環境変数を一元管理します（KABUSYS_ENV によるモード切替あり）。
- auto .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可。
- paper_trading モードでは paper 用 sqlite を使い、本番 DB と分離されます。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                  — 発注関連（BrokerFactory, Engine, OrderManager 等）※詳細実装は別ファイル群
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層 / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py         — （trade_monitor 実装ファイル）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート送信機能）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                      — デフォルトの DB/flag/pid 等の保存先（実行時に自動作成）

補足・運用上の注意
-----------------
- 本番モード（KABUSYS_ENV=live）では KillSwitch の設定や LINE 通知等の設定を慎重に確認してください。validate_config で live 設定時の注意点を表示します。
- ログ: logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリの作成権限に注意）。
- pid / stop / kill flag: data ディレクトリ内のフラグファイルでプロセス制御を行います。誤操作でフラグを残すと意図せず停止するため管理に注意してください。
- AI（OpenAI）呼び出しはコストがかかります。rate limit や API エラーに対するリトライが入っていますが、運用設定は十分に検討してください。

貢献 / 開発
-----------
- まずは config_setup/validate_config でローカル環境を整え、ユニットテスト・静的解析を追加してください。
- DuckDB のデータ（prices_daily / raw_financials / raw_news 等）を用意すると Research / AI 機能の動作確認ができます。
- モジュールは比較的疎結合設計（DB 接続やクライアント注入）なので、モックを使った単体テストが行いやすくなっています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）
- ライセンス情報はリポジトリに含めてください（本 README には含めていません）。

以上。まずは .env を生成 → 設定検証 → 小規模データで Monitoring / Execution をローカルで検証する流れを推奨します。質問や追加したいドキュメント項目があれば教えてください。