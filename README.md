KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
主に以下の機能を持つモジュール群で構成されています。

- 注文の作成・管理・再同期（Execution）
- 監視・アラート・ダッシュボード（Monitoring）
- ポートフォリオ構築（選定・重み付け・株数算出）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント評価）
- Paper Trading 用の分離された検証機能とレポート生成ツール

重要な設計方針：
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離（data/paper_trading.db が既定）。
- 監視（Monitoring）は環境に関わらず本番の sqlite_path を使う（監視の永続化は単一 DB）。
- OpenAI を利用する機能は API キーが必要（環境変数または引数で指定）。

主な機能一覧
-------------
- Execution
  - ExecutionEngine、OrderManager、リコンシリエーション（Reconciler）
  - ブローカー抽象化（実ブローカー / MockBroker）
  - リスク管理（許容比率、回路遮断など）
- Monitoring
  - SystemMonitor（プロセス・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件成立で data/kill.flag を書き込み、Execution を停止）
  - AlertManager（LINE Push による通知）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定、等金額/スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - ニュースを LLM（gpt-4o-mini 等）でスコア化して ai_scores に書き込み
  - レジーム検出（ETF MA + マクロセンチメントの合成）
- Tools
  - paper_verification_report: Paper Trading DB を集計し検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントの | 演算子などを使用）
- SQLite（標準ライブラリ）
- DuckDB（Python パッケージ）
- （OpenAI 機能を使う場合）OpenAI API キー

1) 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 依存ライブラリをインストール
   pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt があればそれを使用してください）

3) データディレクトリを作成（必要に応じて）
   mkdir -p data

4) 環境変数
   プロジェクトルートの .env または OS 環境変数で設定します。自動で .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例とデフォルト）:
   - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
   - SQLITE_PATH: data/monitoring.db
   - DUCKDB_PATH: data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - PID_FILE_PATH: data/execution.pid
   - KILL_FLAG_PATH: data/kill.flag
   - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒, デフォルト 60）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の必須トークン

5) DB 初期化
   監視やツール実行時にコードが自動で必要なテーブルを作成します（init_monitoring_db）。DuckDB テーブルは別プロセスで準備してください（prices_daily / raw_financials 等をロード）。

使い方
------
基本的な起動・ツール実行例を示します。

- ExecutionEngine（売買エンジン）を起動
  - 本番と Paper の切り替え:
    - 本番: KABUSYS_ENV=live python -m kabusys.run_execution
    - Paper:  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 動作:
    - Paper 環境では MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）へ記録して本番 DB とは完全に分離します。
    - 起動時に stop flag（data/stop_requested.flag）が存在している場合は起動をスキップします。
    - エンジンは pid ファイル（data/execution.pid 等）を書き、停止は stop flag を使って行います。

- Monitoring（監視ループ）を起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は本番 sqlite_path を利用して system_status / trade_logs / risk_logs / dashboard 等を永続化します。
  - 監視は ExecutionEngine の生存チェックやデータ鮮度チェックを行い、KillSwitch により必要であれば data/kill.flag を書きます。

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボードを表示します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で変更可）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと Pass/Fail 判定

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出してニューススコアやレジーム判定を行えます。OpenAI API キー（OPENAI_API_KEY）が必要です。

停止フラグ
---------
- 停止（外部からの強制停止）:
  - run_execution.py と run_monitoring.py はそれぞれ project_root/data/stop_requested.flag を監視し、検出したら安全停止します。
- KillSwitch:
  - RiskMonitor 等の評価で条件を満たすと Monitoring 側から data/kill.flag を書き込みます。Execution 側は起動時に kill.flag の存在を確認して必要なら起動を抑制・停止されます。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理（.env 取り扱い）
- run_execution.py                   — ExecutionEngine 起動スクリプト
- run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト

- execution/
  - execution_engine.py              — 実行エンジン本体（EngineConfig など）
  - order_manager.py                 — 注文生成・送信の高レベル API
  - order_repository.py              — DB 永続化
  - reconciler.py                    — 再起動時リコンシリエーション
  - risk_manager.py                  — リスク制御 等
  - broker_factory.py                — Broker クライアント生成（Mock/実装）
  - order_record.py                  — 注文データの純粋ロジック型定義

- monitoring/
  - monitoring_db.py                 — SQLite 永続化層（テーブル・CRUD）
  - system_monitor.py                — CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - trade_monitor.py                 — 注文滞留・約定異常監視
  - risk_monitor.py                  — ドローダウン・ポジション上限チェック
  - kill_switch.py                    — kill.flag 書込みユーティリティ
  - alert_manager.py                 — LINE Push 通知
  - monitoring_engine.py             — 各 Monitor を束ねるループ
  - streamlit_dashboard.py           — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py             — 候補選定・重み付け
  - position_sizing.py               — 株数決定・スケーリング
  - risk_adjustment.py               — セクター制限・レジーム乗数

- research/
  - factor_research.py               — Momentum/Volatility/Value 等の計算（DuckDB）
  - feature_exploration.py           — 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py                      — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py               — マクロ + MA を合成して市場レジーム判定

- tools/
  - paper_verification_report.py     — Paper Trading 結果の検証レポート出力

- utils/
  - process_priority.py              — プロセス優先度・CPU affinity 設定ユーティリティ

データファイル（デフォルト）
---------------------------
- data/monitoring.db            — SQLite（監視ログ・trade_logs・positions・risk_logs・dashboard 等）
- data/paper_trading.db         — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
- data/kabusys.duckdb           — DuckDB（prices_daily / raw_financials / raw_news 等のリサーチデータ）
- data/execution.pid            — Execution の PID ファイル（デフォルト PID_FILE_PATH）
- data/kill.flag                — KillSwitch が書き込む停止理由ファイル
- data/stop_requested.flag      — 外部から run_* を安全に停止するためのフラグ

運用上の注意
-------------
- Paper Trading と本番 DB を必ず分離してください。デフォルトの挙動は設計上分離されていますが、環境変数の設定ミスに注意してください。
- OpenAI の呼び出しはレート制限・ネットワーク障害に備えリトライ実装がありますが、API キーの管理とコストに留意してください。
- プロセス優先度（set_process_priority("high")）を実行しますが、権限不足で失敗する場合はログに警告が出ます。運用環境の権限設定を確認してください。
- Monitoring は本番 sqlite_path を使ってデータを永続化します。監視 DB のバックアップやアクセス制御を検討してください。

開発 & 貢献
------------
- 追加ユニットテスト・型注釈の強化・CI の導入を歓迎します。
- モジュールの責務分離を保ちつつ、DuckDB 上のデータスキーマ（prices_daily, raw_financials, raw_news など）を揃えることでリサーチ機能が正常に動作します。

問い合わせ・参考
----------------
- .env.example を用意して環境変数のテンプレートを管理してください（プロジェクトに含めることを推奨）。
- 実運用前に Paper Trading 環境で十分な検証を行ってください（paper_verification_report を活用）。

以上がプロジェクトの概要と使い方です。必要であれば各コマンドの具体的な実行例や .env のテンプレートを追記します。どの情報を優先して追加しますか？