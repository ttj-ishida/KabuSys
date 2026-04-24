README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を想定した軽量なコードベースです。  
主な機能は取引 Execution、システム/取引の Monitoring、ファクター計算や特徴量探索を行う Research、AI を使ったニュース NLP（センチメント評価）やレジーム判定、ポートフォリオ構築ユーティリティ群、CLI ベースの設定ウィザード／検証ツール群です。

設計上のポイント
- 実行スクリプト（ExecutionEngine / Monitoring）はローカルの SQLite / DuckDB を使用してデータを永続化・分析します。
- Paper Trading モードでは本番 DB と完全に分離された専用 SQLite（data/paper_trading.db）を使用します。
- OpenAI（gpt-4o-mini）を使った NLP 機能があり、API キーを環境変数で指定します。
- 設定は .env（および .env.local）で管理。自動ロード機能を持ち、対話式ウィザードで初期作成できます。

機能一覧
--------
- Execution
  - ExecutionEngine による注文発行フロー（本番/ペーパートレード切替）
  - ブローカークライアント抽象化（MockBroker クライアントを含む）
  - OrderManager / RiskManager / Reconciler 等のコンポーネント
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス稼働・データ鮮度監視
  - TradeMonitor：注文滞留や約定異常検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch 発動
  - MonitoringEngine：各 Monitor をまとめてポーリング・アラート通知
- AI
  - news_nlp.score_news：ニュース記事を集約して LLM でセンチメント評価、ai_scores へ保存
  - regime_detector.score_regime：ETF 勘案＋LLM による市場レジーム評価
- Portfolio（純粋関数群）
  - 候補選定、重み算出、セクター制限、ポジションサイズ算出
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- Tools / CLI
  - config_setup: .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config: 起動前チェック（python -m kabusys.validate_config）
  - paper_verification_report: ペーパートレード結果の検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10+ を想定（typing の記法等を含むため）
- システムに duckdb, psutil 等をインストール可能であること

1. リポジトリをクローン / パッケージを配置
   - パッケージが src/ 配下にある構成のため、プロジェクトルートで作業してください。

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 必要に応じて仮想環境を作成してください。
   - （requirements.txt がある場合は pip install -r requirements.txt を推奨）

3. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（例とデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - PAPER_FILL_MODE — paper_trading での約定モード（instant／partial／never／reject）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. ディレクトリとファイルの権限
   - data/ や logs/ ディレクトリが必要になります。起動スクリプトはログディレクトリを自動作成しますが、アクセス権を確認してください。

基本的な使い方
--------------
起動スクリプト
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中に data/stop_requested.flag を作るとエンジンが停止します。
    - 起動時に実行 PID は data/execution.pid に保存されます（設定により変更可）。
    - プロセス優先度を high に設定します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使って監視 DB を初期化します（冪等）。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、条件に応じて kill.flag を書き込みます。

停止 / Kill Switch
- 停止フラグ:
  - data/stop_requested.flag を作成すると、run_execution・run_monitoring のループが終了またはエンジン停止処理を開始します（実行中プロセスに対する外部停止指示）。
- Kill Switch:
  - RiskMonitor / KillSwitch により条件（ドローダウン超過など）が満たされると data/kill.flag が作られ、ExecutionEngine 側で検出して安全に停止できます。
  - Settings.kill_flag_clear_on_start を 1 にしていると起動時に kill.flag を自動クリアします（本番環境では推奨されません）。

Tools
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可）
  - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等の指標を表示し PASS/FAIL 判定をします。

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging を全スクリプトが利用
- デフォルトで stdout と logs/<app_name>.log（日次ローテート、30日保持）に出力
- ログレベルは LOG_LEVEL または引数で設定可能。ログ保存ディレクトリは LOG_DIR で上書き可能。

AI 機能について
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- LLM 呼び出しはレートリミットやサーバエラーに対してリトライ実装がありますが、API 使用に伴う料金とレート制限には注意してください。
- テスト時は内部の API 呼び出し関数をモックして検証することを推奨します（コード内に差し替え用の注記あり）。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトルート（src 配下の kabusys パッケージを想定）

- src/kabusys/
  - __init__.py                     — パッケージ定義（__version__ 等）
  - config.py                       — Settings クラス（.env / 環境変数読み込み・検証）
  - config_setup.py                 — .env 対話式ウィザード CLI
  - validate_config.py              — 起動前設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py                   — ニュースセンチメント評価（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF + LLM）
  - monitoring/
    - monitoring_db.py              — SQLite 永続化用 DAO
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - system_monitor.py             — CPU/メモリ/データ鮮度監視
    - trade_monitor.py              — （注文）監視ロジック
    - risk_monitor.py               — リスク監視（ドローダウン等）
    - kill_switch.py                — kill.flag の管理
    - alert_manager.py              — （アラート送信実装）
  - execution/
    - execution_engine.py           — ExecutionEngine（発注セッション管理）
    - broker_factory.py             — ブローカークライアントファクトリ
    - order_manager.py              — 注文管理
    - order_repository.py           — 注文永続化
    - reconciler.py                 — 受注整合処理
    - risk_manager.py               — 発注リスク制御
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
    - position_sizing.py            — 株数決定・スケーリング
  - research/
    - factor_research.py            — ファクター計算（Momentum, Volatility, Value）
    - feature_exploration.py        — 将来リターン計算・IC 等
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py              — ロギング設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ群

注意事項 / 運用メモ
-------------------
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨。自動クリアは危険です。
- .env は機密情報を含むため Git にコミットしないでください（config_setup も README ヘッダで注意書きを出力します）。
- Monitoring は本番 sqlite_path を使用するため、環境分離に注意してください（paper_trading は Execution 側で専用 DB を使います）。
- DuckDB のクエリは大量データを扱う設計ですが、適宜インデックスやクエリ範囲を確認してください。
- OpenAI 呼び出し時のレスポンスは LLM 出力の揺らぎを考慮してバリデーション・クリップを行っています。API が変更された場合は呼び出しラッパーの修正が必要になる可能性があります。

お問い合わせ / 開発者向け
-----------------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テスト用途）。
- 単体関数群（portfolio/*, research/*）は DB に依存しない純粋関数が多く、ユニットテストしやすい設計です。
- AI 絡みの外部 API 呼び出しはモック可能な実装になっています（テストでの差し替えを推奨）。

以上。README に不足している点や、運用シナリオ（デプロイ/コンテナ化/CI）の追加ドキュメントが必要であれば、利用目的に合わせて追記できます。