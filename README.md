KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムの一部を実装した Python パッケージです。
本リポジトリには以下の主要機能（バックエンドロジック・監視・リサーチ・AI連携等）が含まれます。

- 実売買を担う ExecutionEngine 周りのコンポーネント（OrderManager / Reconciler / RiskManager 等）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ用ファクター計算（Momentum / Volatility / Value）および特徴量解析
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）と市場レジーム判定（regime_detector）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード など）

主な特徴
--------
- モジュール毎に責務を分離（純粋関数・DB 永続化層・監視等）
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等）
- SQLite を用いた運用ログ・監視データ保存（monitoring.db / paper_trading.db）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（バッチ・リトライ・検証あり）
- Paper Trading (KABUSYS_ENV=paper_trading) による本番環境と分離した検証パス
- LINE を用いたアラート通知（AlertManager）

セットアップ
------------
推奨: 仮想環境を作成して依存をインストールしてください。

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - pip install -r requirements.txt
   - 手動で主要パッケージ例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit

   （requirements.txt が無い場合は上記を個別にインストールしてください）

3. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境 (development | paper_trading | live)
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB とは分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の成行約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）※ run_monitoring 用

例: .env（最小）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development

起動・使い方
------------

コマンドラインでモジュールを直接実行する形を想定しています（パッケージインポートでも同様）。

1. ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - 注意:
     - プロセス優先度を "high" に設定します（set_process_priority）。
     - KABUSYS_ENV が paper_trading の場合、専用の paper_sqlite_path に書き込みます。
     - 起動時に PID ファイルが作成され、kill.flag による停止が可能です。

2. SystemMonitor（単体ポーリングスクリプト）
   - python -m kabusys.run_monitoring
   - 動作:
     - MONITOR_POLL_INTERVAL 環境変数でループ間隔を上書き可能（デフォルト 60 秒）。
     - 監視は KABUSYS_ENV にかかわらず monitoring の sqlite_path を使用します（監視 DB は本番と共有想定）。
     - プロセス優先度を "high" に設定します。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  （PAPER_TRADING_SQLITE_PATH で代替可）
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. 監視ダッシュボード（Streamlit）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - read-only モードで監視用 SQLite を開き、Overview / Positions / Orders / System タブを表示します。

5. AI モジュール（ニューススコア／レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - conn: duckdb.connect(...)
     - target_date: datetime.date 型（評価日）
     - api_key を省略すると環境変数 OPENAI_API_KEY を使用
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - これらはライブラリ関数なので、スクリプトや REPL から呼び出して使います。
   - 注意: OpenAI API 通信に失敗した際はフェイルセーフで安全なデフォルトにフォールバックします（ログ出力あり）。

運用上の注意
-------------
- Kill Switch:
  - RiskMonitor がドローダウンやポジション上限を検出すると、KillSwitch が data/kill.flag を書き込み ExecutionEngine 側で停止シグナルとして扱います。
  - ExecutionEngine 起動時に kill.flag を消去する設定（KILL_FLAG_CLEAR_ON_START）があります。
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブル作成および簡単なマイグレーション（列追加）を行います。
- PID / stale PID:
  - SystemMonitor は PID ファイルを確認し、存在するがプロセスが無ければ stale PID と判定して削除・ログを残します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、本番 DB と分離された PAPER_TRADING_SQLITE_PATH にのみ書き込みます（安全な検証が可能）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py                — パッケージ定義、__version__
- config.py                  — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- order_manager.py
- order_repository.py
- order_record.py
- execution_engine.py
- broker_factory.py
- reconciler.py

src/kabusys/monitoring/
- monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- monitoring_engine.py
- streamlit_dashboard.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py                — ニュース NLP スコアリング（OpenAI）
- regime_detector.py         — マーケットレジーム判定（ETF MA + マクロニュース）

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

実装上の補足
-------------
- DuckDB はリサーチ系の時系列処理に使われ、prices_daily / raw_financials / raw_news 等のテーブルを参照します。
- SQLite は監視ログや発注ログの永続化（軽量 DB）として利用します。
- OpenAI 呼び出し箇所はリトライ・バリデーション・部分書き込み（部分失敗時に既存データ保護）などを行う堅牢な実装になっています。
- process_priority.set_process_priority() により Windows / POSIX の差分を吸収して優先度を設定します（権限不足時は警告でスキップ）。

よくあるコマンドまとめ
---------------------
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を追記してください）

補足・連絡先
------------
不明点や実運用に関する補助が必要であれば、リポジトリの Issue または担当者にお問い合わせください。

--- 
README は実際の環境に合わせて、サンプル .env、requirements.txt、運用手順（systemd / supervisor / Docker など）を追記するとより運用しやすくなります。