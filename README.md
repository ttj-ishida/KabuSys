KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースの小規模フレームワークです。  
主な機能はシグナルに基づく発注（ExecutionEngine）、監視・アラート（Monitoring）、ファクター計算・研究（Research）、ポートフォリオ構築（Portfolio）、および AI を使ったニュースセンチメント評価（AI）です。

特徴
----
- Execution
  - 起動時リコンシリエーション（Reconciler）でブローカーと注文／ポジションを突合
  - Paper trading（KABUSYS_ENV=paper_trading）時は MockBroker を使用し DB を分離
  - リスク管理、注文状態管理（OrderManager / OrderRepository）
- Monitoring
  - システム状態（CPU/Memory/Disk）、データ鮮度、滞留注文、約定異常価格、ドローダウン等の定期監視
  - SQLite ベースの永続化（monitoring_db.init_monitoring_db）
  - LINE によるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル（KillSwitch）
  - Streamlit ダッシュボード（read-only）で監視状況を可視化
- Research / Portfolio
  - DuckDB を使ったファクター計算（Momentum/Value/Volatility など）
  - 将来リターン / IC 計算、ファクターサマリ
  - 候補選定、重み付け、ポジションサイジング、セクター制約、レジーム調整
- AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（ai.regime_detector.score_regime）
- 運用周り
  - プロセス優先度や CPU affinity の設定ユーティリティ（psutil 利用）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 設定は kabusys.config.Settings 経由で一元管理

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - （パッケージ配布時は pip install などに置き換え）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なライブラリをインストール
   - 以下の主要依存が想定されます:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil openai requests streamlit

4. 環境変数 / .env ファイル
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読込されます。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API 用
     - OPENAI_API_KEY — AI 機能を使う場合
     - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を有効にする場合
     - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（必要に応じて上書き）
   - 自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース初期化
   - Monitoring 用の SQLite は各実行スクリプトで自動的に init_monitoring_db が呼ばれて作成・マイグレーションされます。

使い方
------
実行スクリプト（エントリポイントは各ファイルの __main__ を使ってモジュール実行できます）

- Monitoring を起動する
  - 簡易起動:
    - python -m kabusys.run_monitoring
  - 補足:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の監視 DB）を使用します
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil が必要）

- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます
    - 起動時にプロセス優先度を "high" に設定します
    - DuckDB は settings.duckdb_path を使用

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は読み取り専用で開きます（存在しない/開けない場合は警告）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH と併用）

- AI 機能
  - ai.news_nlp.score_news(conn, target_date, api_key=None) — ai_scores テーブルへ銘柄ごとのスコアを書き込む
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み
  - API キーは引数か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

実運用上の注意
- KillSwitch:
  - KillSwitch は監視の中で条件（ドローダウン or ポジション上限超過）を満たした場合、settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine 側がこれを検出して停止することを想定しています。
  - settings.kill_flag_clear_on_start が True の場合、起動時に既存の kill.flag をクリアするよう ExecutionEngine 側で使われます（実装参照）。
- DB マイグレーション:
  - init_monitoring_db は必要なテーブルを作成し、既存 DB にカラムがなければ追加する簡易マイグレーションを行います。
- 優先度設定:
  - set_process_priority はプラットフォームに依存して psutil を利用します。権限不足や未対応 OS の場合は WARN でスキップされます。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py — パッケージメタ情報（__version__ など）
- config.py — 環境設定読み取り（.env 自動ロード / Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード考慮）

パッケージ別
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite の永続化層（テーブル作成 / MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 滞留注文・約定価格異常チェック
  - risk_monitor.py — ドローダウン・ポジション数監視（KillSwitch と連携）
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知クライアント（クールダウン管理）
  - monitoring_engine.py — 各モニタを束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視 UI
- execution/
  - reconciler.py — 起動時リコンシリエーション（Order / Position 突合）
  - order_manager.py — Order State Machine の外向き API（作成・送信・同期等）
  - （他の execution モジュール: broker_factory, execution_engine, order_repository などが想定）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 株数決定・資金配分・単元丸め
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC/統計サマリ
- tools/
  - paper_verification_report.py — paper_trading DB を解析して検証レポートを生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

補足（設計思想の抜粋）
--------------------
- DuckDB は研究・集計処理向けの読み取り専用データ格納に使い、SQL と Python を組み合わせた集計処理を行います。
- 監視系は SQLite を軽量なログ永続化に利用し、MonitoringDB はビジネスロジックを持たない読み書き層です。
- AI 関連は堅牢性を重視し、API のレート制限や一時エラーをエクスポネンシャルバックオフで再試行します。失敗時はフェイルセーフ（スコア 0 や処理スキップ）で運用を継続します。
- ルックアヘッドバイアス防止のため、target_date を明示的に渡し datetime.today()/date.today() を参照しない設計になっています（テスト容易性と再現性を確保）。

ライセンス・貢献
----------------
- （このリポジトリにライセンスファイルがあればここに記載してください）
- バグ報告や機能提案は issue を投げてください。

お問い合わせ
------------
- 実装や設定で不明点があれば、利用者の運用環境やログを添えて質問してください。

以上。README に含めるべき追加の実運用手順（例: systemd ユニットファイル、定期バックアップ、監視ルール）や 開発用の requirements.txt などがあれば教えてください。必要に応じて追記します。