KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python コードベースです。  
主な目的は以下です：
- 戦略用のファクター計算・リサーチ（DuckDB を利用）
- 注文管理・発注実行（ブローカークライアントを抽象化）
- Paper Trading（本番 DB と分離）による検証
- 監視（システム稼働・注文滞留・リスク監視）とアラート（LINE）
- ニュース NLP を用いた AI スコアリング（OpenAI）

特徴
----
- 明確に分離された環境設定（development / paper_trading / live）
- DuckDB を用いた時系列ファクター計算（prices_daily, raw_financials 等）
- SQLite による監視 / トレードログ保存（monitoring.db, paper_trading.db）
- Paper Trading モードでは専用 SQLite（data/paper_trading.db）に記録し本番データと完全に分離
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントと市場レジーム判定（フェイルセーフ・リトライ実装）
- Streamlit ベースの監視ダッシュボード
- kill.flag による外部停止シグナル、LINE によるプッシュ通知
- プロセス優先度・CPU Affinity のユーティリティ（psutil）

セットアップ
-----------
前提
- Python 3.9+
- pip が使える環境

推奨パッケージ（一例）
- duckdb
- psutil
- requests
- openai
- streamlit

例:
1) 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージのインストール（プロジェクトに requirements.txt があればそちらを使ってください）
   - pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトは自動的にプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH / KILL_FLAG_PATH 等のパス設定
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方
-----

1) 監視（MonitoringEngine）を起動
- 監視プロセスは system 状態・注文状態・リスクを定期的にチェックします。
- 起動コマンド（プロジェクトルートで）:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）。
- 補足:
  - monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視ログは常に同一 DB に保存する設計）。

2) ExecutionEngine（発注エンジン）を起動
- live / paper_trading に応じてブローカークライアントや DB が切り替わります。
- 起動コマンド:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 起動時にプロセス優先度が "high" にセットされます（psutil を利用）。

3) Paper Trading 検証レポートの生成
- 過去の Paper Trading DB を集計して検証レポートを標準出力に出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB を指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

4) Streamlit 監視ダッシュボード
- 監視 DB を読み取り専用で表示します。
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- UI でダッシュボード・ポジション・直近注文・システム状態・リスクログなどを確認できます。

5) AI（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）。
- ニュースのスコアリング:
  - kabusys.ai.score_news（モジュール API を通じて呼び出し）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime
- いずれもフェイルセーフ設計（API 問題時は既定値で継続）とリトライ実装があります。

設定の注意点
- PAPER_FILL_MODE の有効値: instant | partial | never | reject（その他は例外）
- KABUSYS_ENV の有効値: development | paper_trading | live（無効値は例外）
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local をロードします。
  - .env.local は .env を上書きします（ただし既存 OS 環境変数は保護されます）。
- kill flag:
  - KillSwitch は data/kill.flag の作成で ExecutionEngine に停止シグナルを送ります（デフォルト path は Settings.kill_flag_path）。
  - ExecutionEngine 起動時に kill flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START）あり。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は主要なソース位置（src/kabusys）と簡単な説明です。

- src/kabusys/
  - __init__.py                 — パッケージ情報（バージョン等）
  - config.py                   — 環境変数 / Settings 管理（.env 自動ロード処理含む）
  - run_monitoring.py           — Monitoring のポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト（paper_trading に対応）
- src/kabusys/monitoring/
  - monitoring_db.py            — SQLite スキーマ初期化と永続化 API
  - system_monitor.py           — CPU/メモリ/Disk/データ鮮度/プロセス生存監視
  - trade_monitor.py            — 注文滞留・約定異常チェック
  - risk_monitor.py             — ドローダウン・ポジション数監視
  - kill_switch.py              — kill.flag 管理ロジック
  - alert_manager.py            — LINE による通知（push）
  - monitoring_engine.py        — Monitor を束ねるエンジン
  - streamlit_dashboard.py      — Streamlit ダッシュボード（監視表示）
- src/kabusys/execution/
  - order_manager.py            — 注文作成 / 送信 / 状態遷移ロジック
  - reconciler.py               — 起動時のリコンシリエーション（注文・ポジション突合）
  - ...（BrokerFactory, EngineConfig, RiskManager などが存在）
- src/kabusys/portfolio/
  - portfolio_builder.py        — 候補選定 / 重み計算
  - position_sizing.py          — 株数決定・スケーリング・lot 単位丸め
  - risk_adjustment.py          — セクター上限・レジーム乗数
- src/kabusys/research/
  - factor_research.py          — momentum/value/volatility 等のファクター計算（DuckDB）
  - feature_exploration.py      — 将来リターン / IC / 統計サマリ
- src/kabusys/ai/
  - news_nlp.py                 — ニュースの LLM センチメント処理（OpenAI 連携）
  - regime_detector.py          — ETF MA + マクロニュースの LLM を使った市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- src/kabusys/utils/
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（運用上の留意点）
--------------------
- 本リポジトリの設計方針として「ルックアヘッドバイアス回避」を徹底しています（date.today() などを直接参照しない設計の箇所あり）。
- AI 系処理は API 失敗時に安全側のデフォルトで継続するよう実装されています（例: macro_sentiment=0.0）。
- Paper Trading モードは本番 DB と完全分離するため、検証で実際の注文を送らない設定が可能です。
- monitoring_db のスキーマは init_monitoring_db() で冪等に作成・マイグレーションを試みます。
- log 出力は標準 logging を使用しており、run_* スクリプトが basicConfig(level=INFO) を設定します。必要に応じて LOG_LEVEL 環境変数で細かく制御できます（Settings.log_level）。

よく使うコマンドまとめ
---------------------
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 貢献
-----------------
- この README はコードベースの理解と運用開始に必要な要点をまとめたものです。  
- 実際の配布・商用利用についてはプロジェクトのライセンス表記（pyproject.toml 等）を確認してください。

以上。必要であれば README に含める詳細なサンプル .env、起動スクリプトの systemd サービス定義や Dockerfile 例なども作成します。どの情報を追加しますか？