KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための Python パッケージです。本コードベースはトレード実行（ExecutionEngine）、監視（MonitoringEngine）、ファクター計算やリサーチ、AI を使ったニュースセンチメント評価などのコンポーネントで構成されています。DuckDB を用いた時系列データ処理、SQLite による監視・注文ログの永続化、OpenAI API を用いたニュース解析などの機能を持ちます。

主な特徴
--------
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパー取引の切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock ブローカーでペーパー取引を完全分離）
  - リスク管理（最大ポジション比率・利用上限など）
  - 再起動時リコンシリエーション（注文状態・ポジション同期）
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）とプロセス監視
  - 注文滞留・約定異常検出
  - ドローダウン / ポジション上限監視 → kill.flag で ExecutionEngine 停止指示
  - LINE によるアラート通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築（Portfolio）
  - 候補選定、等額 / スコア重み付け、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC 計測・特徴量サマリー（外部依存を最小化）
- AI（OpenAI）連携
  - ニュース記事を LLM でセンチメント評価し ai_scores に書込む（score_news）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（score_regime）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil）
  - .env ファイルの自動読み込み（プロジェクトルートを探索）

セットアップ（開発環境）
--------------------
以下は最小構成の手順例です。実際のプロダクション環境では適宜監視・起動スクリプト・サービス定義等を用意してください。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて）その他（pytest 等）

   例:
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt はリポジトリに含まれていないため、実行に必要なライブラリを上記からインストールしてください。

3. データディレクトリ作成
   - デフォルトの DB パスは data/ 以下です。最低でも data ディレクトリを作成しておくと便利です。
     - mkdir -p data

環境変数（主なもの）
-------------------
アプリ設定は環境変数または .env / .env.local で指定できます。プロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動読み込みされます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な変数（一部）:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、Mock ブローカーで完全分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須で使用箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須で使用箇所あり）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に利用
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー取引用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH: PID / kill flag の保存先（デフォルトは data/ 以下）
- PAPER_FILL_MODE: ペーパートレードにおける約定モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring が参照。デフォルト 60）

簡単な .env 例:
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な起動コマンド）
--------------------------

- 監視の起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を read-only で開きます（MonitoringEngine 実行中に参照する用途）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 簡易的に稼働率 / 注文成功率 / レイテンシ等を集計して PASS/FAIL を出力します。

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date のニュースウィンドウに対してセンチメントを ai_scores テーブルへ書き込みます。
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します（未設定だと ValueError）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込みます。

注意点 / 運用上のヒント
-----------------------
- 自動 .env ロード
  - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
  - テスト時などで自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- kill.flag
  - KillSwitch は条件成立で kill.flag（デフォルト: data/kill.flag）を書き込み、ExecutionEngine に停止指示を送ります。ExecutionEngine 側は起動時にこのファイルを検査/削除する設計です（設定によりクリアの挙動を制御可）。
- Paper Trading
  - paper_trading モードは本番 DB と完全分離されるよう設計されています。ローカルで試す際は KABUSYS_ENV=paper_trading を指定してください。
- OpenAI
  - API 呼び出し時はレート制限・ネット障害に対してリトライやフェイルセーフの実装がありますが、API キーは厳重に管理してください。
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びますが、権限や OS により効果が異なります（psutil に依存）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- run_monitoring.py — Monitoring のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — SQLite を使った監視ログ永続化層（init / CRUD）
- system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス監視
- trade_monitor.py — 注文滞留・約定異常検出
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag を書き込むロジック
- alert_manager.py — LINE push 通知
- monitoring_engine.py — 各 Monitor を束ねる実行ループ
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py / order_repository.py / reconciler.py / execution_engine.py / ...（注文管理、再コンシリエーション、リスク管理等）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 発注株数決定（lot 単位、リスク制限、スケール調整）
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
- feature_exploration.py — 将来リターン / IC / 統計サマリー

src/kabusys/ai/
- news_nlp.py — ニュースセンチメントの LLM 連携ロジック
- regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/utils/
- process_priority.py — psutil を利用した優先度 / CPU affinity 設定

実行時のログ / DB
------------------
- 監視ログ: SQLite（デフォルト data/monitoring.db）に system_status / trade_logs / positions / risk_logs / dashboard を格納
- DuckDB: 時系列価格データや raw_financials などの大規模分析用に使用（data/kabusys.duckdb デフォルト）

貢献・拡張のヒント
-------------------
- DuckDB スキーマ（prices_daily / raw_financials / raw_news 等）に合わせて research / ai モジュールを拡張可能
- BrokerClientFactory を実装すれば別ブローカーへの接続が可能（kabuステーション API など）
- モニタリングのしきい値や通知ポリシーは Settings / 環境変数で動的に調整できるようにしてください

ライセンス / その他
------------------
この README ではライセンス情報は含めていません。配布・利用時はプロジェクト内の LICENSE を参照してください。

以上。必要であれば、README に入れる具体的な .env.sample、systemd 起動例、Dockerfile、依存パッケージの pinned requirements.txt なども作成します。どれを追加しますか？