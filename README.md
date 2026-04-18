# KabuSys

日本株向け自動売買システムのコアライブラリ群と実行スクリプト群です。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ/ポートフォリオ構築、AIベースのニュース評価などの機能が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - ExecutionEngine（発注実行）の起動
  - Monitoring（監視）の起動
  - Paper Trading 検証レポート
  - AI モジュール（ニュース/Llm）実行の注意点
- 主要ファイル・ディレクトリ構成
- 注意事項 / 運用メモ

---

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム向けのライブラリ群です。  
主な用途は次のとおりです:

- 発注エンジン（ExecutionEngine）の起動・運用（実口座／ペーパートレード両対応）
- システム稼働状況・注文・リスクの監視（Monitoring）
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算（Portfolio）
- DuckDB を使ったファクター算出やリサーチ（Research）
- OpenAI を利用したニュースセンチメント評価（AI モジュール）
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading レポート等）

コードベースはモジュール化されており、スクリプトからの実行やライブラリとしての利用がしやすい設計になっています。

機能一覧
--------
主要機能（抜粋）:

- Execution
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化（paper_trading 時は MockBrokerClient）
  - ExecutionEngine による発注制御、OrderManager/OrderRepository、RiskManager、Reconciler 等の組立

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor: 注文の滞留 / 約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視（dashboard / positions 更新）
  - KillSwitch: 条件で data/kill.flag を書き込み、ExecutionEngine を停止させる
  - MonitoringEngine: 各 Monitor を束ねて定期実行

- Portfolio（純粋関数群）
  - 候補選定、等金額／スコア加重、セクター制約、レジーム乗数、株数決定（単元丸め・集約キャップ適用）

- Research
  - DuckDB 経由でファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算・IC 計算・統計サマリー）

- AI
  - ニュース NLP（OpenAI を使用）: 銘柄ごとのセンチメントを ai_scores に保存
  - レジーム判定（ma200 + マクロニュース sentiment を合成）

- ユーティリティ
  - 環境設定ウィザード（.env 生成/更新）
  - 設定検証（必須環境変数・config/*.yaml 等のチェック）
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 用ユーティリティ

セットアップ手順
---------------
以下は基本的なローカルセットアップ手順です。実運用では OS 権限やサービス化等を適切に行ってください。

1. リポジトリをクローン
   - git clone ...

2. Python 環境を準備
   - 推奨: Python 3.9+（コードは typing/構文上それ以上を想定）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がない場合は主要依存ライブラリをインストールしてください:
     - pip install duckdb psutil openai
     - （任意）PyYAML（config/*.yaml の検証に利用）：pip install PyYAML

4. 環境変数設定（.env）
   - 初回はウィザードを使うと簡単です（下記参照）。
   - 手動で設定する場合はプロジェクトルートに .env を作成してください。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - OPENAI_API_KEY（AI モジュールを使用する場合）
     - LOG_LEVEL / LOG_DIR
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

使い方
------

1) 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 対話形式で .env を生成・更新します。生成後は必ず git にコミットしないでください。

2) 設定検証
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い (exit 1) になります。

3) ExecutionEngine（発注実行）の起動
   - 通常起動:
     - python -m kabusys.run_execution
   - ペーパートレードモード（DB は data/paper_trading.db に分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行時の挙動:
     - 起動時にプロセス優先度を "high" に設定し、各コンポーネントを初期化します。
     - data/stop_requested.flag が存在すると起動をスキップまたは停止します。
     - 実行中の PID は data/execution.pid に書き込まれます（PID ファイルパスは Settings で変更可能）。

4) Monitoring（監視）の起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - SystemMonitor, TradeMonitor, RiskMonitor 等を使いポーリング監視を行います。
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
     - 監視は本番の sqlite_path を使用（KABUSYS_ENV に依存せず本番監視 DB に書きます）。
     - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）で行います。

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - ペーパートレード用 SQLite を読み取り、稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を出力します。

6) AI モジュール（ニュース NLP / レジーム判定）
   - OpenAI API を利用します。事前に OPENAI_API_KEY を設定してください。
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ai_scores に書き込み
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込み
   - 注意:
     - API キーが未設定だと例外になります。
     - 使用モデルは gpt-4o-mini（コード内定義）。API 利用料やレート制限に注意してください。
     - LLM 呼び出しはリトライやフェイルセーフの仕組みを含みますが、運用ではコスト管理を行ってください。

主要ファイル / ディレクトリ構成
----------------------------
（抜粋、主要モジュールのみ）

- src/kabusys/
  - __init__.py                  — パッケージ定義
  - config.py                    — Settings / 環境変数自動ロード機構
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py           — ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py        — プロセス優先度 / CPU affinity
  - execution/
    - execution_engine.py        — ExecutionEngine（本体）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                 — OpenAI を使ったニュースセンチメント
    - regime_detector.py          — マクロ + MA200 を使ったレジーム判定
  - tools/
    - paper_verification_report.py

ログ / データ / フラグファイル
----------------------------
- logs/                      — ログファイル（logging_setup が作成）
  - execution.log
  - monitoring.log
- data/
  - monitoring.db             — デフォルト SQLite 監視 DB
  - paper_trading.db          — ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時に使用）
  - kabusys.duckdb            — デフォルト DuckDB（分析用）
  - execution.pid             — ExecutionEngine の PID（デフォルト）
  - stop_requested.flag       — run_* スクリプトが監視する停止フラグ
  - kill.flag                 — KillSwitch によって書き込まれる停止フラグ

注意事項 / 運用メモ
------------------
- KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかを指定します。live 設定は本番実行のため慎重に。
- .env は絶対にソース管理（Git など）にコミットしないでください（API キーやパスワードを含む）。
- run_monitoring は監視用 DB に書き込むため、モニタリング環境の DB 設定に注意してください（Monitoring は環境にかかわらず本番 sqlite_path を使用します）。
- paper_trading モードでは MockBrokerClient が用いられ、データは paper_trading.db に分離されます（本番 DB と完全に分離されます）。
- OpenAI を使う機能を利用する場合は API キーと使用料に注意してください（モデルは gpt-4o-mini）。
- ログディレクトリ作成やプロセス優先度設定は実行権限に依存します。必要に応じて権限・サービス化してください。
- 設定検証ツール（validate_config）は PyYAML 未導入時に YAML 内容検証をスキップします。config/*.yaml を使う場合は PyYAML のインストールを推奨します。

サンプルコマンドまとめ
--------------------
- 環境ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution (通常):
  - python -m kabusys.run_execution

- Execution (paper_trading):
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を指定: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB を利用: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

この README はコードベースから抽出した情報に基づいて作成しています。実運用時は README の手順に従いつつ、各環境に合わせた追加設定（systemd / supervisor などでのプロセス管理、バックアップ、権限管理、モニタリングの外部連携等）を行ってください。