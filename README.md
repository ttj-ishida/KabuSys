README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を行う小規模なシステムです。本リポジトリは以下の主要機能群を含みます。

- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（システム監視・注文監視・リスク監視・アラート送信）
- Portfolio construction（候補選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な設計方針は「本番データと検証用データの分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しは明示的でフェイルセーフにすること」です。

機能一覧
--------
- Execution
  - ブローカークライアントを抽象化（本番・Paper Trading 切替）
  - OrderManager による注文生成、状態同期
  - Reconciler による起動時リコンシリエーション（注文・ポジションの突合）
  - リスク管理（RiskManager 等、設定に基づく制限）
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、Execution プロセス死活、データ鮮度監視
  - TradeMonitor：滞留注文、約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件を満たした場合の停止フラグ書き込み（data/kill.flag）
  - AlertManager：LINE Messaging API による通知（クールダウン管理付き）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定（スコア・ランク）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp: OpenAI を使った銘柄ごとのニュースセンチメント集計・ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースセンチメントの合成による市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を読み検証レポートを出力
  - DB 初期化（監視用テーブル等）ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈で PEP 604 などを利用しているため）
- SQLite（組み込み）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
インストール例（venv を推奨）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. data ディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成（自動読み込みされます）
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...         （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...（アラートを LINE に送る場合）
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. DB 初期化
   - Monitoring 用の SQLite は各起動スクリプトが init_monitoring_db を呼び出してくれます。明示的に初期化する場合は起動時に自動で作成されます。

使い方
------
1. Monitoring の起動（監視ループ）
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）
   - 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します

2. ExecutionEngine の起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、Paper Trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録されます（本番 DB と分離）
   - 実行中の PID はデフォルト data/execution.pid に書き込まれます
   - 強制停止トリガーは data/kill.flag（KillSwitch により書き込まれる）または data/stop_requested.flag により監視プロセスが検出して停止します

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で別の SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで監視 DB を開いて表示します

5. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です
   - 関数として呼び出す例：
     - kabusys.ai.score_news(conn, target_date, api_key=...)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意
- KABUSYS_ENV の有効値は development / paper_trading / live です。不正な値を設定すると Settings が例外を投げます。
- PAPER_FILL_MODE の有効値は instant / partial / never / reject です。
- Monitoring は常に「本番 SQLITE_PATH」を参照して監視ログを保存します（設計上環境に依らず同じ監視 DB を使う）。
- Execution は paper_trading の場合に別 DB を使用します（本番 DB とデータ分離）。
- プロセス優先度設定は psutil を使って行われます。権限不足等で設定できない場合は警告が出ますが処理は継続します。
- KillSwitch はリスク条件（ドローダウンやポジション上限）を満たした際に data/kill.flag を書き込み ExecutionEngine 側で検知して停止するため、手動でのクリア（KillSwitch.clear()）が必要な場面があります。

主要ディレクトリ構成
--------------------
（src/kabusys 以下の主要ファイル・モジュール）

- run_monitoring.py           — SystemMonitor ポーリングループ起動
- run_execution.py            — ExecutionEngine 起動スクリプト
- config.py                   — 環境変数 / 設定管理
- __init__.py                 — パッケージ情報（__version__ 等）

- monitoring/
  - monitoring_db.py          — SQLite テーブル定義・永続化層
  - system_monitor.py         — CPU/メモリ/Disk・データ鮮度・PID チェック
  - trade_monitor.py          — 注文滞留・約定異常検出
  - risk_monitor.py           — ドローダウン・ポジション上限チェック
  - kill_switch.py            — 停止フラグ管理
  - alert_manager.py          — LINE 通知用ユーティリティ
  - monitoring_engine.py      — 各 Monitor の束ね（テスト用 run_once / 本番 run）
  - streamlit_dashboard.py    — Streamlit ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - execution_engine.py
  - broker_factory.py
  - ...（発注関連）

- portfolio/
  - portfolio_builder.py      — 候補選定・重み付け
  - position_sizing.py        — 発注株数算出
  - risk_adjustment.py        — セクターキャップ・レジーム乗数

- research/
  - factor_research.py        — Momentum / Volatility / Value
  - feature_exploration.py    — 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py               — ニュースセンチメント取得（OpenAI）
  - regime_detector.py        — 市場レジーム判定（ma200 + macro sentiment）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
  - __init__.py

- utils/
  - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

サンプル環境変数（.env 例）
--------------------------
# 基本
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API / トークン
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# LINE 通知
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# 動作設定
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60

貢献・拡張
----------
- 新しいブローカークライアントを追加する場合は execution/broker_factory.py と BrokerAPIProtocol を実装してください。
- AI モデルやプロンプトの改善は ai/news_nlp.py / ai/regime_detector.py を編集してください（リトライ・バリデーションロジックは保守的に扱っています）。
- テストを追加する場合は monitoring_engine.run_once を使ったユニットテストが書きやすいです。

ライセンス
---------
プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください。

以上。必要であれば、README に付け加えるサンプル .env.example や起動スクリプトの具体的なコマンド例（systemd ユニット、Dockerfile など）のテンプレートも作成します。どの情報を追加しますか？