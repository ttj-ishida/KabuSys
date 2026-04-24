KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。
主な機能は、注文実行エンジン（ExecutionEngine）、監視サブシステム（Monitoring）、
ポートフォリオ構築・サイズ決定ロジック、リサーチ（ファクター計算・特徴量解析）、
およびニュースに基づく AI スコアリングなどを含みます。

このリポジトリは、以下のような実運用を想定した構成要素を含みます：
- Execution（発注処理、リスク管理、注文履歴）
- Monitoring（プロセス・システム・注文監視、Kill Switch）
- Portfolio（銘柄選定・重み算出・ポジションサイズ計算）
- Research（ファクター計算、IC 等の統計解析）
- AI（ニュース NLP によるセンチメント集計、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定）
- CLI ツール（.env 作成ウィザード、設定検証、ペーパートレード検証レポート）

主な機能一覧
--------------
- 環境設定管理
  - .env/.env.local の自動ロード（Settings クラス）
  - 対話式ウィザードで .env を生成/更新（config_setup）
  - 設定検証 CLI（validate_config）: 必須環境変数・パス・YAML 構文等の事前検出
- 実行エンジン（Execution）
  - ブローカークライアント抽象化（実ブローカー / モックを切り替え）
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）
  - Order 管理・履歴記録（SQLite + DuckDB）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では本番 DB と分離して data/paper_trading.db を使用
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard テーブル（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - ログ出力とアラート送信（LINE 等は環境変数で設定）
- ポートフォリオ構築
  - 候補選定、等重・スコア重みの計算
  - セクター上限の適用、レジームに基づく乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap のスケーリング）
- リサーチ
  - DuckDB 上で動作するファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Spearman）・統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント判定し ai_scores に書き込み
  - 市場レジーム判定（ETF とマクロニュースの合成スコア）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動します。
   - 例: git clone ... && cd <repo_root>

2. Python 仮想環境を作成して有効化（任意推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストールします（requirements.txt が無い場合は以下を参考に）。
   - 主要依存例:
     - duckdb
     - psutil
     - openai  (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を有効にする場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは手動で .env をルートに作成（.env.example を参考に）。

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

6. データディレクトリやログディレクトリの初期化
   - data/ や logs/ は自動作成されますが、権限等に注意してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知に使用）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading でのモック約定挙動: instant|partial|never|reject）

使い方（実行例）
----------------

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成するとループが検出して終了します（停止フラグファイル方式）。
    - または Ctrl+C（KeyboardInterrupt）。

- 実行エンジンを起動（発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBroker が使われ、paper_trading 用 DB に記録されます。
    - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
  - 実行中は PID を data/execution.pid に出力します。停止リクエストは data/stop_requested.flag を作成してください。

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニューススコアを生成できます（api_key 引数または OPENAI_API_KEY 環境変数が必要）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止フラグ / Kill Switch
-----------------------
- 実行エンジンと監視ループはプロジェクトルート下の data/stop_requested.flag を参照し、これが存在すると安全に停止します（run_monitoring/run_execution にて使用）。
- Kill Switch（監視サブシステム）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存されます（kabusys.utils.logging_setup）。
- コンソール出力は stdout に出力されます。

ディレクトリ構成（主要ファイル）
--------------------------------
（以下は src/kabusys 配下の主要モジュールを抜粋した構成図です）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py        — monitoring 用 SQLite 永続化層
      - system_monitor.py       — システム・データ鮮度監視
      - trade_monitor.py        — 注文ログ監視（滞留注文等）
      - risk_monitor.py         — ドローダウン / ポジション上限監視
      - kill_switch.py          — Kill Switch ロジック（kill.flag 書込み）
      - monitoring_engine.py    — 各 Monitor を束ねるエンジン
      - alert_manager.py        — （アラート送信機能）
    - execution/
      - execution_engine.py     — 実行エンジン（Engine の本体）
      - order_manager.py        — 注文管理
      - order_repository.py     — 注文履歴リポジトリ
      - broker_factory.py       — ブローカークライアント生成
      - reconciler.py           — 注文再整合
      - risk_manager.py         — 実行時リスク管理
    - portfolio/
      - portfolio_builder.py    — 候補選定・重み算出
      - position_sizing.py      — 株数決定ロジック
      - risk_adjustment.py      — セクター制約・レジーム乗数
    - research/
      - factor_research.py      — Momentum/Volatility/Value 等の計算
      - feature_exploration.py  — 将来リターン・IC・統計サマリー
    - ai/
      - news_nlp.py             — ニュース NLP（OpenAI 連携）
      - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
    - data/                      — 実行時データ（SQLite / DuckDB / flag / pid 等）
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - utils/
      - logging_setup.py        — ログ初期化ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

補足 / 注意事項
--------------
- デフォルト設定では監視 DB（monitoring.db）をプロジェクト内の data/ に作成します。運用時は適切なパスへ変更してください（DUCKDB_PATH/SQLITE_PATH）。
- KABUSYS_ENV を "live" にした場合は本番運用になります。LINE 通知や Kill Switch の設定等を十分に確認してください。
- OpenAI を用いる AI 機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しは失敗時にフォールバックする設計ですが、利用量やコストにご注意ください。
- DuckDB は多くのリサーチ機能で必須です。SQLite は監視・注文履歴用に使用しています。
- ログディレクトリ作成やプロセス優先度設定には OS の権限が関わるため、実行環境の権限設定に注意してください。

ライセンス・貢献
----------------
本 README はコードベースの概要説明です。実際のライセンス・貢献ルールはリポジトリ上の LICENSE / CONTRIBUTING ファイルを参照してください。

以上。必要であれば README に含めるサンプル .env テンプレートや、より詳細な起動フロー（ExecutionEngine の設定項目や RiskConfig の説明）を追加します。どの箇所をより詳しく書きたいか教えてください。