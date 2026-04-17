KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。  
主な目的は「戦略の研究（DuckDB）」「発注エンジン（kabuステーション / MockBroker）」「稼働監視・リスク管理」「AI を使ったニュース評価」です。  
このリポジトリはモジュール化されており、ローカル開発・ペーパートレード・本番（live）を切り替えて動かせます。

主要機能
-------
- 環境設定ウィザード（.env の対話式生成）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- ExecutionEngine（発注エンジン）：本番/ペーパートレード切替、リスク管理、注文管理
- Monitoring（System / Trade / Risk の監視、Kill Switch）
- Portfolio 構築ユーティリティ（候補選択・重み算出・ポジションサイズ算出）
- Research（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- Paper Trading 検証レポート生成ツール

前提（依存）
------------
推奨 Python 3.10+。主要ライブラリ:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 検証用、無くても動作するが警告が出ます）

セットアップ手順
---------------
1. レポジトリをクローン・チェックアウト
2. 仮想環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存インストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は最低限 duckdb, psutil, openai をインストール）
4. data ディレクトリを作成（PID/フラグや DB のデフォルトパスがここを使います）
   - mkdir -p data
5. 環境変数設定
   - 対話式で .env を作る: python -m kabusys.config_setup
   - または .env を直接作成（.env.example を参照）
6. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたいとき: python -m kabusys.validate_config --strict

重要な環境変数（主なもの）
-------------------------
必須:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

運用関連（デフォルト値は括弧内）:
- KABUSYS_ENV (development | paper_trading | live)（development）
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に使用
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（0 推奨）

AI 関連:
- OPENAI_API_KEY — news_nlp / regime_detector などで使用

動作に影響するその他:
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）

自動 .env 読み込み
------------------
起動時にプロジェクトルートを探索して .env / .env.local を自動読み込みします。  
この自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方
------

基本的なコマンド（パッケージモードで実行）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV により本番 / ペーパートレード挙動が変わります。
    - paper_trading: MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を使って監視レコードを保存します（環境に依存せず本番 path を参照します）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

プロセス停止・Kill スイッチ
--------------------------
- run_execution / run_monitoring は data/stop_requested.flag や data/kill.flag を使って外部から停止や Kill シグナルを送る仕組みを持ちます。
  - stop_requested.flag: 監視・実行ループを穏やかに終了させるために利用（run_* スクリプトが見る）
  - kill.flag: KillSwitch による ExecutionEngine 停止トリガー（Monitoring が検出して書き込む）
- ExecutionEngine の PID ファイルは data/execution.pid（デフォルト）に書かれます。SystemMonitor はこの PID を検査して実プロセスの稼働を確認します。

AI（OpenAI）機能
----------------
- ニュースのセンチメント解析: kabusys.ai.news_nlp.score_news — DuckDB の raw_news と news_symbols を参照し、ai_scores に書き込みます。OpenAI API キー（OPENAI_API_KEY）が必要です。
- レジーム検出: kabusys.ai.regime_detector.score_regime — ETF 1321 の MA200 とマクロニュースの LLM評価を合成して market_regime に書き込みます。こちらも OPENAI_API_KEY が必要です。
- API 呼び出しは再試行や失敗時のフェイルセーフ（デフォルトで macro_sentiment=0.0 等）を組み込んでいます。

開発者向けメモ
--------------
- 自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml のあるディレクトリ）を基準に行います。テストなどで無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- config.py の Settings はプロパティベースで環境変数をラップしています。値検証（enum 等）を行うため、無効な値は ValueError になります。
- DB 周り:
  - DuckDB: 分析用（prices_daily / raw_financials 等）
  - SQLite: 監視ログ・注文履歴用（monitoring.db / paper_trading.db）

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
- config_setup.py — .env を対話式に生成するウィザード
- validate_config.py — 環境/設定の静的検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ（機能別）
- ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（ma200 + LLM）
- monitoring/
  - monitoring_db.py — SQLite の監視用テーブル作成・簡易ラッパー
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — 条件に応じて kill.flag を書く
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py — （未完/実装想定）通知管理
- execution/ (発注関連: BrokerFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager)
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・リスク制限
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/バリュー/ボラティリティファクター
  - feature_exploration.py — forward returns、IC、統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/*.py, ai/*.py, portfolio/*.py, research/*.py などは、それぞれ説明した役割を持ち、可能な限り副作用を抑えた純粋関数や DB ラッパーで構成されています。

よくある質問
------------
Q: ペーパートレードと本番 DB は分離されていますか？  
A: はい。KABUSYS_ENV=paper_trading のとき、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。Monitoring は常に sqlite_path（本番用 path）を使用します（監視は本番 DB に対して行う設計）。

Q: MONITOR_POLL_INTERVAL の単位は？  
A: 秒です。0 以下や無効な値は無視され、デフォルト 60 秒が使われます。

Q: OpenAI キーが無くても起動できますか？  
A: はい。ただし ai/news_nlp や regime_detector を呼ぶ処理は OpenAI キーが無いと動作せず、呼び出し側で例外を投げます。Monitoring 等、他の多くの機能はキー不要です。

ライセンス / 貢献
----------------
本プロジェクトのライセンス情報・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（無ければ管理者へ問い合わせてください）。

補足
----
- 実運用では LOG_LEVEL や KILL_FLAG_CLEAR_ON_START 等の設定を慎重に確認してください。特に KABUSYS_ENV=live のときは LINE 通知設定や Kill スイッチの扱いに注意が必要です。
- 各モジュール内の docstring に詳細設計（期待する入力/出力・副作用）が記載されています。実装や拡張を行う際は先に docstring を参照してください。

お問い合わせ
------------
不明点やバグは issue を作成してください。開発者向けの設計議論は PR を通じて行ってください。