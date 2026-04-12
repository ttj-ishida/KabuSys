KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
戦略・ポートフォリオ構築、ポジションサイズ計算、発注管理、起動時のリコンシリエーション、監視・アラート、ニュースの NLP によるセンチメント評価など、運用に必要な主要コンポーネントを含みます。

主な特徴
---------
- ExecutionEngine（発注エンジン）
  - ブローカー抽象化（本番 / Paper Trading 切替）
  - OrderManager／OrderRepository による状態管理
  - 再起動時リコンシリエーション（Reconciler）
  - リスクマネージャ（注文上限・ドローダウン等）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等配分／スコア加重、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ算出（単元丸め、aggregate cap）
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: MA200 とマクロセンチメントを組み合わせた市場レジーム判定
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（monitoring_db）
  - LINE 経由のアラート（AlertManager）、kill.flag による Execution 停止シグナル
  - Streamlit ダッシュボード（読み取り専用）
- 運用ツール
  - paper_verification_report: Paper Trading の検証レポート生成

動作環境・前提
--------------
- Python 3.9+（typing の記述や一部の構文から推奨）
- 以下の主な依存パッケージ（例）:
  - duckdb
  - psutil
  - openai（OpenAI SDK）
  - requests
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3, logging, argparse 等

セットアップ
-----------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他のライブラリを追加）

3. プロジェクトルートに .env を作成（自動読み込み機能あり）
   - ルートは .git または pyproject.toml を基準に検出する
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development   # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...

4. データディレクトリ作成
   - mkdir -p data

5. （任意）Paper Trading 用 DB は run_execution 起動時に指定 DB を自動的に使うため、特別な初期化は不要。monitoring DB は起動時にテーブル作成（冪等）されます。

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 起動環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します（本番 DB と分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）

使い方
------

1. ExecutionEngine（発注エンジン）起動
   - モジュール実行:
     python -m kabusys.run_execution
   - 実行時の挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に取引ログを記録し、本番 DB と完全分離します。
     - プロセス優先度を "high" に設定します（set_process_priority）。
     - duckdb および sqlite 接続を確立します。
     - リコンシリエーション（再起動時の同期）・エンジン実行を行います。

2. Monitoring（監視）起動
   - モジュール実行:
     python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
     - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視データは本番 DB に保存）。
     - SystemMonitor（プロセス・CPU/メモリ/ディスク/データ鮮度）、TradeMonitor（滞留注文・約定異常）、RiskMonitor（ドローダウン・ポジション上限）を実行し、必要に応じて kill.flag を書きます。
     - LINE トークンが設定されている場合は AlertManager を通じて通知が可能（cooldown 管理あり）。

3. Streamlit ダッシュボード（読み取り専用）
   - 起動例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 機能:
     - ダッシュボード集計、オープンポジション、最近の発注ログ、最新システムステータス、リスクログを表示します（読み取り専用で DB は read-only で開くことを推奨）。

4. Paper Trading 検証レポート
   - レポート生成:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     --db で SQLite ファイルを明示的に指定可能（デフォルト環境変数または data/paper_trading.db）。

5. AI モジュール（プログラム的に利用）
   - ニューススコアリング:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="...")

   - レジームスコア:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="...")

注意事項 / 運用メモ
-----------------
- Monitoring の DB スキーマは init_monitoring_db で自動作成・マイグレーションされます（冪等）。
- kill.flag の存在で ExecutionEngine を停止する仕組みです。KillSwitch は重いリスク（ドローダウンやポジション上限）で flag を作成します。run_execution 起動時に kill.flag をクリアするかどうかは Settings.kill_flag_clear_on_start で制御可能。
- Paper Trading は本番 DB と完全分離されることを意図しています（PAPER_TRADING_SQLITE_PATH）。
- process priority（優先度）や CPU affinity は utils/process_priority.py で抽象化しています。権限不足等で失敗してもログ出力してスキップします。
- OpenAI を利用する機能は API の呼び出しに失敗した場合にフェイルセーフ（0 ベースやスキップ）で進める設計です。APIキーが未設定だと例外を投げる箇所もあります。

ディレクトリ構成
----------------
概略（src/kabusys 配下、主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングスクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite ベースの永続化層
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みロジック
    - alert_manager.py            — LINE 通知
    - monitoring_engine.py        — Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - ...                         — 発注関連（OrderManager, Reconciler, BrokerFactory 等）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み
    - position_sizing.py           — 株数算出・aggregate cap
    - risk_adjustment.py           — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py          — ファクター算出
    - feature_exploration.py      — 将来リターン・IC 等
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP スコアリング
    - regime_detector.py          — 市場レジーム判定
  - monitoring/                   — （前述）
  - tools/
    - __init__.py
    - paper_verification_report.py

ライセンス・貢献
----------------
本リポジトリのライセンス情報や貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
------
この README はコードベースから抽出した情報に基づく導入・運用ガイドラインです。実運用では環境ごとの設定管理（秘密情報の安全な保管）、バックアップ、監視ログの運用手順、OpenAI API 利用料やレート制限の考慮、テスト運用（Paper Trading）を十分に行ってください。質問や追記したい点があれば教えてください。