README
=====

概要
----
KabuSys は日本株の自動売買システムのコードベースです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: ブローカーとやり取りして注文を発行・管理する実行エンジン
- Monitoring: システム稼働状況・注文状況・リスク監視と通知（LINE）/ダッシュボード
- Portfolio: 銘柄選定・重み付け・ポジションサイジングに関する純粋関数群
- Research: ファクター計算・特徴量探索ユーティリティ（DuckDB 経由）
- AI モジュール: ニュース NLP（OpenAI）による銘柄センチメント／市場レジーム判定
- Tools: Paper Trading の検証レポート生成スクリプト等

主な設計方針:
- DuckDB / SQLite をデータ層に利用（prices_daily / raw_news / monitoring 等）
- Paper Trading と Live は DB を分離（paper_trading モード時は data/paper_trading.db）
- 自動化された監視・キルスイッチにより危険状態での自動停止をサポート
- 外部 API 呼び出し（OpenAI 等）は適切にリトライ・フェイルセーフ化

機能一覧
--------
- Execution:
  - 注文作成・送信、状態遷移管理（OrderManager）
  - 再起動時のリコンシリエーション（Reconciler）
  - RiskManager（発注制限、ドローダウンなど）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ書き込み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（簡易 UI）
  - Monitoring DB（SQLite）へのログ永続化
- Portfolio:
  - 銘柄候補選定、等配分・スコア加重配分、リスク調整、株数計算（単元丸め、キャップ処理）
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI:
  - ニュースを LLM でスコアリングし ai_scores に保存（news_nlp）
  - マクロ + ETF MA200 を合成して市場レジーム判定（regime_detector）
- Tools:
  - paper_verification_report: Paper Trading DB を読み検証レポートを出力

前提条件 / 依存
---------------
推奨 Python バージョン: 3.10 以上（型ヒントに | を使用）
主な依存パッケージ:
- duckdb
- psutil
- requests
- openai（OpenAI SDK）
- streamlit（ダッシュボード）
- sqlite3（標準ライブラリ）
- その他ユーティリティ（必要に応じて）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo_url>

2. 作業ディレクトリ / 仮想環境
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存をインストール
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit

   ※ 実運用では requirements.txt / Poetry 等で依存管理してください。

4. データディレクトリの作成
   - mkdir -p data

5. 環境変数（.env）の用意
   - プロジェクトルートに .env（または .env.local）を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 重要な変数例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO

6. データベース初期化
   - Monitoring 用テーブルは実行スクリプト（run_monitoring / run_execution）から自動作成されます（init_monitoring_db）。

実行方法（使い方）
----------------

実行環境の指定:
- KABUSYS_ENV を指定して挙動を切り替えます。
  - development: 開発向け
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
  - live: 本番

パッケージをインポート可能な状態にする（開発時）:
- export PYTHONPATH=src
- あるいはパッケージをインストール (pip install -e .)

1) ExecutionEngine を起動
- デフォルト（本番 DB）:
  - python -m kabusys.run_execution
- Paper Trading モード:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - このモードでは MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

停止:
- ExecutionEngine は data/stop_requested.flag を監視します。外部から停止させる場合はこのファイルを作成してください。
- また、KillSwitch が条件を満たすと data/kill.flag を作成し Engine に停止シグナルを送ります。

2) Monitoring を起動
- python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で上書き可能:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 最小 1 秒、デフォルト 60 秒。

Monitoring の動作:
- monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）に常に書き込みます（KABUSYS_ENV にかかわらず本番 monitoring DB を使用）。

3) Streamlit ダッシュボード（監視 UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視データを読み取り専用で表示します（起動中の MonitoringEngine が DB を生成/更新します）。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

5) AI モジュールの利用
- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使ってニューススコア / レジーム判定を行えます。実行には OPENAI_API_KEY が必要。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト data/kill.flag）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用

停止 / フラグ運用
----------------
- data/stop_requested.flag:
  - run_execution/run_monitoring スクリプトはこのファイルの存在を監視し、検知時に安全に停止します。
- data/kill.flag:
  - KillSwitch により作成され、ExecutionEngine に即時停止を促します（部分失敗を防ぐため）。

ディレクトリ構成
----------------
以下は主要ファイルとモジュールの概観（src/kabusys 内）です。実際のツリーはリポジトリに依存します。

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — Settings（環境変数/.env 読み取り）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計関数
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py       — 市場レジーム判定（ETF MA + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 + MonitoringDB ラッパー
    - system_monitor.py        — CPU/メモリ/プロセス/データ鮮度監視
    - trade_monitor.py         — 注文滞留/約定異常検出
    - risk_monitor.py          — ドローダウン・ポジション制限監視
    - kill_switch.py           — kill.flag の作成/管理
    - alert_manager.py         — LINE Push 通知ラッパー
    - monitoring_engine.py     — 各 Monitor を束ねるループ
    - streamlit_dashboard.py   — Streamlit ベースの監視 UI
  - execution/
    - order_manager.py         — 注文の外向き API
    - reconciler.py            — 再起動時リコンシリエーション
    - order_repository.py      — （実装ファイルは省略したが存在）
    - ...                      — ブローカー／リスク管理等
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity のユーティリティ
  - data/                      — （実行時に使用する、デフォルト DB 等）

補足 / 運用上の注意
------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading 環境でも監視 DB が本番 DB と同じ場合は運用上の分離に注意してください（コード上は monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています）。
- OpenAI 呼び出しや外部 API はネットワークエラーやレート制限を考慮したリトライ処理が実装されていますが、API キー漏洩・コスト等には十分ご注意ください。
- データのバックアップや DB マイグレーション（monitoring_db には軽微なマイグレーション処理あり）を運用ルールで検討してください。

ライセンス / 貢献
----------------
- README 内の説明は開発担当者向けの簡易ドキュメントです。実際の運用・配布前に LICENSE / CONTRIBUTING をプロジェクトに追加してください。

問い合わせ
----------
- 実装の詳細や設計意図についてはソース内の docstring / コメントを参照してください。追加のドキュメントや使い方例が必要であれば、どの機能に対してかを指定してご依頼ください。