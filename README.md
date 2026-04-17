KabuSys — 日本株自動売買システム
===============================

このリポジトリは、シンプルな日本株自動売買システムのコア部分（注文実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング等）を集めたモジュール群です。  
README は開発者向けの簡易ドキュメントで、プロジェクトの概要、主要機能、セットアップ・起動手順、使い方、ディレクトリ構成を説明します。

要点
----
- Python 3.10+ を想定（PEP 604 の `X | None` 構文等を使用）。
- メイン機能: ExecutionEngine（発注・リスク管理・再同期）、Monitoring（システム・注文監視・Kill Switch）、ポートフォリオ構築、ファクター計算、AI ニュースセンチメント評価、Streamlit ダッシュボード、紙上検証レポート生成。
- DB: SQLite（監視用 / Paper Trading 用）と DuckDB（価格・リサーチ用）。デフォルトパスは data 以下（設定で上書き可）。
- 環境変数は .env / .env.local / OS 環境変数から読み込まれる（設定モジュールで自動読み込み、無効化可）。

機能一覧
--------
- Execution (run_execution.py)
  - ブローカークライアントを通じた発注処理（本番 or Paper Trading 切替）
  - OrderManager / RiskManager / Reconciler による発注フロー・リスク管理・自動復旧
  - Paper Trading 環境では MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用
- Monitoring (run_monitoring.py, monitoring package)
  - SystemMonitor: CPU・メモリ・ディスク・Execution プロセス・データ鮮度の監視（ログは SQLite）
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録、kill.flag の発行
  - AlertManager: LINE Messaging API によるアラート送信（クールダウン付き）
  - Streamlit ダッシュボードによる監視 UI（read-only 接続）
- Portfolio（portfolio package）
  - 銘柄候補選定、等金額／スコア加重の配分計算、セクター上限適用、ポジションサイズ計算（単元丸め・キャップ適用）
- Research（research package）
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン計算、IC（ランク相関）や統計サマリ
  - DuckDB を使った SQL + Python 実装
- AI（ai package）
  - news_nlp: raw_news を結合して OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定（market_regime テーブルへ書込）
  - 両方とも OpenAI API のリトライ・バリデーションロジックを備える
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率/成功率/レイテンシ/リスク却下 等）
- DB マイグレーション
  - monitoring_db.init_monitoring_db() が必要テーブルを冪等に作成・マイグレーション（カラム追加等）を実施

セットアップ手順
----------------
※ 以下は開発環境向けの手順例です。プロダクション運用時は適宜プロセス管理（systemd / supervisor など）や secrets 管理を行ってください。

1. Python と仮想環境
   - Python 3.10+ を用意
   - 推奨: 仮想環境作成
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 主要依存: duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （requirements.txt が存在すれば pip install -r requirements.txt）

3. リポジトリからの実行を容易にするため（任意）
   - パッケージを editable install:
     - pip install -e .

4. 設定 (.env)
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env（または .env.local）を置けます。
   - 自動読み込みは既定で有効。テスト時に無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 例（.env）:
     - KABUSYS_ENV=development          # development | paper_trading | live
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant         # instant|partial|never|reject
     - MONITOR_POLL_INTERVAL=60

5. data ディレクトリ作成（必要に応じて）
   - mkdir -p data

使い方（主なコマンド）
---------------------

1. 監視プロセス起動（Monitoring）
   - 機能: SystemMonitor をポーリングし monitoring DB（デフォルト data/monitoring.db）へログ
   - デフォルト動作: MONITOR_POLL_INTERVAL=60 秒
   - 実行方法:
     - (a) パッケージインストール済み:
       - python -m kabusys.run_monitoring
     - (b) 直接スクリプト実行:
       - python src/kabusys/run_monitoring.py
   - 停止方法:
     - プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検出して終了する。
   - 注意: run_monitoring は「環境（KABUSYS_ENV）にかかわらず」本番 sqlite_path を使用します（監視ログは本番 DB を参照）。

2. 実行エンジン起動（Execution）
   - 機能: ExecutionEngine を起動し注文フローを実行。KABUSYS_ENV によって MockBroker (paper_trading) と実ブローカーを切替。
   - 実行方法:
     - python -m kabusys.run_execution
     - または python src/kabusys/run_execution.py
   - Paper Trading:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ保存され本番 DB と分離されます。
     - PAPER_FILL_MODE で約定の振る舞いを設定（instant/partial/never/reject）。
   - 停止・制御:
     - data/stop_requested.flag の検出で Engine を停止（run_execution は起動時に既に flag がある場合は起動せず終了）。
     - kill.flag（KillSwitch）が生成された場合は ExecutionEngine による安全停止が試行されます。
   - PID 管理:
     - 実行時に data/execution.pid を利用／作成する仕組みがあります（Settings.pid_file_path で上書き可）。

3. Streamlit 監視ダッシュボード
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で SQLite DB を参照し、Overview/Positions/Orders/System のタブを表示します。

4. Paper Trading 検証レポート
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - オプションで期間指定:
       - --from YYYY-MM-DD --to YYYY-MM-DD
       - --db PATH で DB を指定（PAPER_TRADING_SQLITE_PATH 環境変数を上書き可能）
   - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、最終的な PASS/FAIL 判定を標準出力に表示。

5. AI / リサーチ関数の利用
   - ライブラリ的に関数をインポートして利用可能:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - kabusys.research.calc_momentum / calc_volatility / calc_value など（DuckDB 接続を渡す）
   - 注意: OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定する必要あり。

設定（Settings）について
------------------------
- main 設定クラス: kabusys.config.Settings（settings オブジェクトでアクセス可能）
- 自動ロード順序: OS 環境 > .env.local > .env（プロジェクトルートで検索）
- 主な環境変数:
  - KABUSYS_ENV: development | paper_trading | live（動作モード）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（外部 API 用の必須トークン）
  - OPENAI_API_KEY（AI モジュール）
  - SQLITE_PATH（監視 DB, default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
  - DUCKDB_PATH（prices/financials を格納する DuckDB, default: data/kabusys.duckdb）
  - PID_FILE_PATH, KILL_FLAG_PATH 等（監視・停止に関するパス）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

データベースについて
--------------------
- monitoring DB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブルを init_monitoring_db() が作成・マイグレーションします。
- Paper Trading は本番監視 DB とは分離して専用 SQLite を使用（PAPER_TRADING_SQLITE_PATH）。
- DuckDB: 大量時系列データ（prices_daily、raw_financials、raw_news 等）の分析用に想定。

停止・Kill 動作
----------------
- 停止フラグ: data/stop_requested.flag を置くと run_monitoring/run_execution のループが検出して終了します。
- KillSwitch: RiskMonitor 等の判定により data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルとして扱われます。kill.flag は明示的にクリアする API（KillSwitch.clear）があります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py     — Paper Trading 検証レポート CLI
- monitoring/
  - monitoring_db.py                 — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (他の実装ファイル)
  - broker_factory.py
  - （ブローカー API の抽象・実装等）
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
  - process_priority.py
  - __init__.py
- data/ (実行時に使用されることが多いディレクトリ例)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - stop_requested.flag
  - kill.flag
  - execution.pid

開発上の注意
-------------
- type annotations と標準ライブラリのみで書かれた箇所が多く、外部依存は限定されていますが、実行には duckdb, psutil, openai, requests, streamlit などが必要です。
- .env 読み込みは Settings モジュール内で自動的に行われます。テスト時など自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 環境は本番 DB と明確に分離するよう設計されていますが、監視プロセス（run_monitoring）は monitor 用 DB（Settings.sqlite_path）を参照します。運用時は適切にパスを設定してください。
- OpenAI やブローカー API の呼び出しはネットワーク依存であり、リトライやフォールバックロジックを備えていますが、API キー漏洩等には注意してください。

例: 開発用の簡単な開始フロー
1. 仮想環境を作り依存をインストール
   - python -m venv .venv && source .venv/bin/activate
   - pip install duckdb psutil openai requests streamlit
2. .env を作成して必要なキーを設定
3. データディレクトリ作成
   - mkdir -p data
4. 監視プロセス起動（別ターミナルで）
   - python -m kabusys.run_monitoring
5. 実行エンジン起動（別ターミナルで）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. Streamlit ダッシュボード（ブラウザで表示）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
7. 検証レポート（Paper Trading DB に対して）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 責任
-----------------
（この README にはライセンス情報は含まれていません。実際の配布物では LICENSE を追加してください。）  
自動売買ロジックは実運用に使う前に十分なテストとレビューを行ってください。特に実際のブローカー接続や資金を用いる場合は自己責任で運用してください。

補足・問い合わせ
-----------------
実装の詳細や特定コンポーネント（例: ExecutionEngine の設定、BrokerClient の実装、AI 呼び出しのテスト方法）についての追記が必要であれば、どの部分を深掘りしたいか教えてください。README を用途（開発者向け、運用向け、デプロイ手順付き）に合わせて拡張できます。