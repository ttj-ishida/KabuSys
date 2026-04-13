KabuSys
=======

日本株向けの自動売買システムのコードベースです。戦略・ポートフォリオ構築、発注実行、監視・アラート、研究用ファクター計算、AI を使ったニュースセンチメント等の機能を含みます。

概要
----
KabuSys は以下の役割を持つ主要コンポーネント群で構成されています。

- ExecutionEngine（発注・リスク管理・リコンシリエーション）  
  - ブローカークライアント経由で注文を発行し、OrderRepository に状態を永続化。paper_trading モードでは MockBrokerClient を使用し本番 DB と分離します。
- Monitoring（システム・注文・リスク監視）  
  - SystemMonitor / TradeMonitor / RiskMonitor で監視を行い、LINE への通知や kill flag による ExecutionEngine 停止を行う仕組みがあります。監視結果は SQLite（data/monitoring.db）へ保存されます。
- Portfolio（銘柄選定・重み付け・株数計算）  
  - 候補選定、等重・スコア加重、リスク調整、ポジションサイズ計算など純粋関数で実装。
- Research（ファクター計算・特徴量分析）  
  - DuckDB 上の prices_daily / raw_financials 等を参照してファクター（モメンタム・ボラティリティ・バリュー等）を計算、IC 等の分析機能を提供。
- AI（ニュース NLP / レジーム判定）  
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント集約 / 市場レジーム判定。結果は DuckDB の ai_scores / market_regime テーブルへ保存。
- ユーティリティ・ダッシュボード  
  - Streamlit ダッシュボード、環境変数ロードユーティリティ、プロセス優先度設定など。

主な機能一覧
--------------
- 発注管理（OrderManager）: 発注作成・送信、2相永続化、拒否ハンドリング
- リコンシリエーション（Reconciler）: 再起動時の注文・ポジション同期
- リスク管理（RiskManager）: ポジション上限やドローダウンの監視（RiskMonitor）
- 監視（MonitoringEngine）: システム・注文滞留・約定異常などの定期チェック、LINE 通知、kill flag 発行
- ポートフォリオ構築: 候補選定、重み付け（等重・スコア重み）、単元株丸め、リスク調整（セクターキャップ、レジーム乗数）
- 研究モジュール: モメンタム/ボラティリティ/バリュー計算、将来リターン、IC、統計サマリー
- AI 集約: ニュースを LLM でスコア化し ai_scores に保存、マクロニュースからレジームを判定
- Streamlit ダッシュボード: 監視 DB の可視化
- Paper Trading 用ツール: 検証レポート生成スクリプト

必要条件（想定）
----------------
- Python 3.10 以上（PEP 604 の | 型注釈等を使用）
- 主要外部パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
- SQLite（標準ライブラリで使用）
- ネットワーク（LINE API / OpenAI 利用時）

セットアップ手順
----------------
1. リポジトリをクローンします。
   - git clone <repo-url>

2. 仮想環境を作成して有効化します（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストールします（requirements.txt がある場合）。
   - pip install -r requirements.txt  
   本リポジトリに requirements.txt がない場合は少なくとも以下をインストールしてください:
   - pip install duckdb psutil requests streamlit openai

4. data ディレクトリを作成します（必要に応じて）。
   - mkdir -p data

5. 環境変数を設定します。プロジェクトルートの .env / .env.local を使えるようにしています（自動ロード）。テスト時や自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（Settings で参照）
--------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (LINE 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視DB デフォルト: data/monitoring.db) — Monitoring は常にこの本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading のとき Execution はこの DB を使用
- PAPER_FILL_MODE (paper_trading 時の fill モード: instant|partial|never|reject、デフォルト "instant")
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアする場合 "1")
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)

使い方（主要スクリプト）
-----------------------

1) 監視ループを起動（Monitoring）
- デフォルトで MONITOR_POLL_INTERVAL=60 秒
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番パス）を使用します。

コマンド:
- python -m kabusys.run_monitoring

設定例:
- MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

挙動:
- プロセス優先度を "high" に設定し、SystemMonitor.check_once() を定期実行して monitoring DB に書き込みます。
- stale PID 検出やデータ鮮度チェック等のリスクイベントを記録します。

2) 実行エンジン起動（Execution）
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

コマンド:
- python -m kabusys.run_execution

例（Paper Trading）:
- KABUSYS_ENV=paper_trading python -m kabusys.run_execution

処理:
- ブローカークライアント作成 → OrderRepository / OrderManager / RiskManager 等を組み立て → ExecutionEngine.run_session()

3) Streamlit ダッシュボード
- 監視 DB を読み取り専用で可視化します。

コマンド:
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
- paper_trading DB を読み取り、稼働率・注文成功率・レイテンシ等を出力します。

コマンド:
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

注意事項・挙動メモ
-----------------
- Monitoring は常に settings.sqlite_path を使用します（環境にかかわらず監視ログは本番 DB パスへ）。
- Execution は KABUSYS_ENV=paper_trading のとき settings.paper_sqlite_path を使用し、本番 DB とは分離されます。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書きできます（正の整数、デフォルト 60 秒）。
- Process priority と CPU affinity の設定は utils/process_priority.py でプラットフォームを抽象化して行います。設定に失敗しても警告を出してスキップします。
- AI 機能（ニューススコア / レジーム判定）は OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フォールバック（失敗時は安全側の値）を組み込んでいます。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動ロードします。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュール・ファイル）
- __init__.py
- config.py
  - Settings：環境変数 / .env の読み込み・検証
- run_monitoring.py
- run_execution.py

- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite スキーマ / MonitoringDB（永続化層）
  - system_monitor.py           — システム状態・データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — kill.flag 書き込みロジック
  - alert_manager.py            — LINE push 通知クライアント
  - monitoring_engine.py        — 各 monitor を束ねる
  - streamlit_dashboard.py      — Streamlit ベースの監視 UI

- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照されるが省略)
  - execution_engine.py (参照されるが省略)
  - broker_factory.py, broker_api.py (参照されるが省略)
  - risk_manager.py (参照されるが省略)

- portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 株数計算・スケールダウンロジック
  - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py          — momentum/value/vol calc（DuckDB）
  - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - __init__.py

- ai/
  - news_nlp.py                 — ニュースセンチメント集約（OpenAI）
  - regime_detector.py          — MA + マクロセンチメントによるレジーム判定
  - __init__.py

- tools/
  - paper_verification_report.py — paper_trading DB の検証レポート

- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ

拡張・開発のヒント
------------------
- 多くの関数（portfolio、research 等）は副作用のない純粋関数として設計されています。単体テストが書きやすい構造です。
- DuckDB にロードするデータ（prices_daily, raw_financials, raw_news 等）を整備すれば、research / ai モジュールをオフラインで検証できます。
- OpenAI への外部呼び出し部分は小さなラッパー関数で切り出してあるため、テスト時はモック化（patch）して安定化できます。
- .env の読み込み順序は OS 環境 > .env.local > .env（.env.local は上書き）。OS 環境を保護するため .env ロードは保護機能付き。

ライセンス / 連絡
----------------
この README はコードベースの参照ドキュメントです。ライセンスや詳細な運用手順・安全性の考慮（実資金運用時の注意点）は別途ドキュメントにまとめてください。

---

必要であれば、README に含めるサンプル .env のテンプレート、詳細な依存関係（requirements.txt の内容候補）、運用手順（デプロイ / systemd ユニット例）なども作成します。どれを追加しますか？