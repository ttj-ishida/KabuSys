KabuSys — 日本株自動売買システム (README)
========================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模な Python コードベースです。  
主な設計方針は以下の通りです。

- DuckDB / SQLite を用いたローカルデータ処理（外部 API 呼び出しを最小化）  
- 実行（ExecutionEngine）と監視（MonitoringEngine）を分離し、冪等・フェイルセーフを重視  
- Paper Trading（検証）モードを用意し、本番 DB と完全分離可能  
- LLM（OpenAI）を用いたニュース NLP / レジーム判定を補助機能として実装

主な機能
--------
- Execution（発注エンジン）
  - Broker クライアント抽象化（paper_trading モードでは Mock を使用）
  - OrderManager による発注ワークフロー（作成→送信→同期／再送）
  - Reconciler による起動時リコンシリエーション（OrderSent の復旧、ポジション差分検出）
  - RiskManager / OrderRepository 等（リスク管理・DB 永続化）

- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK・プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウンやポジション上限監視・ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボードでの可視化

- Portfolio Construction
  - 候補選定、等重／スコア重み付け、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算（単元丸め、Aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、特徴量サマリ

- AI (OpenAI)
  - news_nlp: raw_news を LLM でセンチメント評価し ai_scores に書き込む
  - regime_detector: マクロニュース + ETF MA200 乖離を合成して市場レジーム判定

セットアップ
-----------
1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - このリポジトリに requirements.txt がない場合、最低限次を入れてください:
     - pip install duckdb psutil requests openai streamlit
   - 他に使用する環境やテストに応じて追加パッケージが必要になる可能性があります。

3. データディレクトリの作成
   - デフォルトの DB / PID / フラグファイルは data/ 以下に置かれます:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視ログ)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/execution.pid (ExecutionEngine PID)
     - data/kill.flag (Kill switch flag)
   - 必要に応じて環境変数でパスを上書きできます（下記参照）。

4. 環境変数 (重要)
   - 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API（必須の場合）
     - KABU_API_PASSWORD: kabuステーション API（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）を有効にする場合
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject、デフォルト instant)
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。0以下の値は無視されデフォルトが使われる。
     - PID_FILE_PATH, KILL_FLAG_PATH, その他閾値: CPU_THRESHOLD_PCT 等

使い方
------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）
  - run_monitoring は常に本番用 sqlite_path を使います（監視ログは本番 DB に保存）

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB とは完全分離）
  - 起動時に Reconciler による復旧処理などが実行されます

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を read-only で開いて表示します

- Paper Trading 検証レポート生成（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション例:
    - --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易な合格/不合格判定（稼働率、注文成功率、送信率、P95 レイテンシ等）

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続が必要
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意点 / 運用上のポイント
-------------------------
- .env の自動読み込み
  - プロジェクトルート (.git または pyproject.toml がある場所) を基に .env / .env.local を読み込みます。
  - OS 環境変数が優先され、.env.local は既存変数を上書きします。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading
  - KABUSYS_ENV=paper_trading に設定すると paper_trading 専用の SQLite を使用し、本番 DB に影響を与えません。
  - PAPER_FILL_MODE で MockBroker の約定挙動を制御できます（instant / partial / never / reject）。

- PID / Kill flag
  - 実行エンジンは起動時に PID を data/execution.pid に書き、SystemMonitor はその PID の存否を監視します。
  - KillSwitch は条件成立時に data/kill.flag を書き、実行エンジンに停止シグナルを伝達します。
  - kill.flag の自動クリアの挙動は Settings で制御できます。

- LINE 通知
  - AlertManager は channel_access_token と user_id が空の場合は送信をスキップしログ出力のみ行います。
  - 同一カテゴリ/レベルに対してクールダウン（デフォルト 30 分）を行います。

ディレクトリ構成（主なファイル）
-------------------------------
以下は src/kabusys 以下の主なファイルと概要（抜粋）です。

- src/kabusys/
  - __init__.py              -- パッケージ定義（__version__ 等）
  - config.py                -- 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py        -- SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py         -- ExecutionEngine 起動スクリプト（paper_trading 対応）
- src/kabusys/monitoring/
  - monitoring_db.py         -- SQLite スキーマ初期化・永続化ラッパー（MonitoringDB）
  - system_monitor.py        -- CPU/MEM/DISK・データ鮮度・プロセス監視
  - trade_monitor.py         -- 滞留注文・約定異常検出
  - risk_monitor.py          -- ドローダウン・ポジション上限監視
  - kill_switch.py           -- フラグファイルによる停止シグナル管理
  - alert_manager.py         -- LINE Push API による通知
  - monitoring_engine.py     -- 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py   -- Streamlit ベースの監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py         -- 発注フローの高レベル API
  - reconciler.py            -- 起動時の注文・ポジション再同期ロジック
  - ... (broker / engine / risk 等の実装を含む)
- src/kabusys/portfolio/
  - portfolio_builder.py     -- 候補選定・重み付け
  - position_sizing.py       -- 株数計算・単元丸め・aggregate cap
  - risk_adjustment.py       -- セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py       -- Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py   -- 将来リターン計算・IC・統計サマリ
- src/kabusys/ai/
  - news_nlp.py              -- OpenAI を用いたニュースセンチメントスコアリング
  - regime_detector.py       -- マクロニュース + ETF MA200 によるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py -- Paper Trading の検証レポート生成スクリプト
- src/kabusys/utils/
  - process_priority.py      -- プロセス優先度・CPU affinity 設定ユーティリティ

その他
-----
- DB スキーマの初期化は各起動スクリプト内で init_monitoring_db() が呼ばれるため、通常は手動マイグレーションは不要です（冪等）。
- AI 機能では OpenAI の JSON mode を利用して厳密な JSON を期待する実装になっています。API キーやレートリミットに注意してください。
- log レベルは Settings.log_level 等で制御できます（環境変数 LOG_LEVEL）。

ライセンスや貢献
----------------
（この README には含まれていません。必要であればプロジェクトの LICENSE, CONTRIBUTING などを追加してください。）

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。実行時に不明点やエラーが出る場合は、ログの出力を確認し、必要な環境変数や DB ファイルの存在をチェックしてください。追加でドキュメント化してほしい箇所があればお知らせください。