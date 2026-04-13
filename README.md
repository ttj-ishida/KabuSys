KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群です。戦略・ポートフォリオ構築、実行エンジン、監視（Monitoring）、AI を用いたニュース解析／レジーム判定、研究用ファクター計算などを含みます。

主な特徴
--------
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文滞留・リスク監視、LINE 通知・kill.flag）
- Paper Trading モード（本番 DB と完全分離された模擬発注）
- DuckDB を用いたファクター計算（prices_daily / raw_financials を参照）
- OpenAI を使ったニュースセンチメント（AI scoring）および市場レジーム判定
- Streamlit ダッシュボード（監視データ可視化）
- 各種ユーティリティ（プロセス優先度設定、ポートフォリオ構築、ポジションサイズ計算等）

動作環境・前提
--------------
- Python 3.9+（型ヒントで | を使用しているため 3.10 推奨）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit（ダッシュボード用）
  - openai（AI 機能を使う場合）
- SQLite（標準ライブラリの sqlite3 を使用）

セットアップ手順（ローカル）
------------------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージのインストール（最小例）
   - pip install duckdb psutil requests streamlit openai

   （プロジェクト配布パッケージや requirements.txt がある場合はそちらを使用してください。）

4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルト: development
  - paper_trading の場合、MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

使い方（代表的な起動例）
-----------------------

1. 監視ループ（SystemMonitor 単体）
   - 実行: python -m kabusys.run_monitoring
   - 説明:
     - PIDファイルや kill.flag の管理、monitoring DB 初期化を行い、SystemMonitor のポーリングを継続実行します。
     - MONITOR_POLL_INTERVAL でポーリング間隔を設定できます（秒）。

2. 実行エンジン（ExecutionEngine）
   - 実行: python -m kabusys.run_execution
   - 説明:
     - 設定に応じて実ブローカー or MockBroker（paper_trading）を選択し、ExecutionEngine を起動します。
     - 起動時にリコンシリエーション（Reconciler）を実施して状態同期を行います。
     - 実行中は pid_file を書き、kill.flag による停止シグナルに対応します。

3. Streamlit ダッシュボード（監視表示）
   - 実行: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視用 SQLite を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート（コマンドライン）
   - 実行例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - または: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   - 説明:
     - data/paper_trading.db（または指定 DB）から指標（稼働率、注文成功率、レイテンシ等）を集計し標準出力へレポートを出します。

5. AI 関連（プログラム的に利用）
   - ニュースセンチメント（ai.score_news）
     - 例（Python から）:
       - from kabusys.ai.news_nlp import score_news
       - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
   - レジーム判定（ai.regime_detector.score_regime）
     - 例（Python から）:
       - from kabusys.ai.regime_detector import score_regime
       - score_regime(conn, target_date, api_key="...")

注意点・運用メモ
--------------
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。paper_trading は run_execution 側で分離された paper_sqlite_path を使用します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine 起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足等で失敗してもワーニングを出して継続します。
- kill.flag（KILL_FLAG_PATH）を書き込むことで ExecutionEngine に停止シグナルを送る設計です。KillSwitch は監視側で評価・出力します。
- DuckDB/SQLite の書き込みはトランザクション管理を行っていますが、運用中は定期的なバックアップを推奨します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数/.env ローダ、Settings クラス
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py           — monitoring DB 初期化 / MonitoringDB（永続化 API）
- system_monitor.py          — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- trade_monitor.py           — 注文滞留 / 約定異常監視
- risk_monitor.py            — ドローダウン・ポジション上限監視
- kill_switch.py             — kill.flag 制御
- alert_manager.py           — LINE プッシュ通知ラッパ
- monitoring_engine.py       — 各モニター束ねるエンジン
- streamlit_dashboard.py     — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py
- reconciler.py
- （その他: broker_factory, execution_engine, order_repository 等が存在）

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定・重み付け
- position_sizing.py         — 発注株数計算（ロット丸め・集約キャップ）
- risk_adjustment.py         — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py         — Momentum/Volatility/Value 等のファクター計算（DuckDB）
- feature_exploration.py     — 将来リターン計算 / IC / 統計サマリー

src/kabusys/ai/
- news_nlp.py                — ニュースを OpenAI でスコアリングして ai_scores に書き込む
- regime_detector.py         — ma200 とマクロニュースを合成して market_regime を算出

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

ユーティリティ
- src/kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定

開発・拡張のヒント
-----------------
- DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。テーブルスキーマに合わせてデータを投入してください。
- AI 機能を使う場合は OPENAI_API_KEY を設定してください（関数は api_key 引数で上書き可能）。
- テスト時は設定読み込みを無効化したり、OpenAI 呼び出し関数をモックする設計になっています（内部で呼び出しをラップしているため差し替えが容易です）。
- portfolio / position sizing の関数群は純粋関数（副作用なし）なのでユニットテストが容易です。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください）

お問い合わせ
------------
実運用・導入に関する質問はリポジトリの issue または担当者へご連絡ください。

以上。README に載せるべき追加の運用ルールや組織固有の設定があればお知らせください。