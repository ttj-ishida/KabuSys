README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。シグナル生成やポートフォリオ構築、注文実行、監視・アラート、Paper Trading（検証用）やResearch用のファクター計算、そしてニュースNLP / レジーム判定を含む補助機能を提供します。本リポジトリは主にライブラリ群（src/kabusys/...）とコマンド/スクリプト群で構成されています。

主な特徴
--------
- ExecutionEngine 起動スクリプト（実際の注文送信を行うエンジン）
  - 本番 / Paper Trading を環境変数 KABUSYS_ENV で切替可能（paper_trading は MockBrokerClient と専用 DB を使用）
- Monitoring（System / Trade / Risk）およびアラート
  - SQLite 監視DB にログを保持、LINE による通知機能を持つ AlertManager
  - Kill Switch 機能により閾値超過時に ExecutionEngine に停止シグナルを送出
  - Streamlit ベースの監視ダッシュボード（read-only）
- Portfolio 構築ユーティリティ（候補選定、スコア/等分配、リスク調整、ポジションサイズ計算）
- Research モジュール（ファクター計算、forward returns、IC計算、統計サマリー）
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成スクリプト
- ユーティリティ
  - 環境設定ローダ（.env/.env.local を自動読み込み、無効化オプションあり）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（Windows / POSIX 対応）

セットアップ
----------
前提
- Python 3.9+（ソースの型ヒントやモジュール使用を想定）
- SQLite は標準搭載。下記外部パッケージをインストールしてください。

推奨パッケージ（例）
- duckdb
- psutil
- requests
- streamlit
- openai

インストール例（仮に pipenv/venv を利用する場合）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

3. 開発時にソースをパッケージとして使う場合（任意）
   - pip install -e .

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API を使う機能で必要（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境 "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading: MockBrokerClient 使用、data/paper_trading.db に書き込み（本番 DB と分離）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH — Monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, その他しきい値（CPU/MEM/DISK など）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動読み込みを無効化

.env の自動読み込み
- プロジェクトルートは .git または pyproject.toml を探索して決定します。
- 自動で .env を読み、続けて .env.local を上書き読みします（OS 環境変数は保護）。
- 必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

使い方
------
一般的にソースを PYTHONPATH に含めるかインストール後、モジュールとして実行します。
例（プロジェクトルートで実行できる場合）:

ExecutionEngine を起動（本番/テスト運用）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に書き込みます。
  - 起動時にプロセス優先度を "high" に設定します（権限がない場合は警告が出ます）。

Monitoring の長期ポーリング（SystemMonitor 単体）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視ログは SQLITE_PATH に保存されます（監視は常に sqlite_path を使用）。

Streamlit ダッシュボード（監視UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - GUI でダッシュボード、保有ポジション、最近の注文、システム状態等を閲覧できます（read-only）。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD （開始日）
  - --to YYYY-MM-DD （終了日）
  - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
- 出力: 稼働率、注文成功率、送信率、レイテンシ統計、PASS/FAIL 判定を標準出力へ表示します。

AI 機能（プログラム呼び出し）
- ニュースセンチメント付与:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
    - conn は duckdb.connect(...) の接続オブジェクト
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

監視・アラートの仕組み（概略）
- SystemMonitor: CPU/MEM/DISK/プロセス生存確認、データ鮮度チェック（DuckDB の get_last_price_date を利用）
- TradeMonitor: 滞留注文（stale）・約定時価格異常をチェックし risk_logs に記録
- RiskMonitor: ダローダウンやポジション上限を評価し、必要時に KillSwitch による停止フラグを作成
- AlertManager: LINE Push API を使ってクールダウン付きで通知を送信

注意事項
- Monitoring の DB 初期化は init_monitoring_db() により冪等的に行われます（マイグレーション処理あり）。
- Monitoring は実行環境にかかわらず sqlite_path（本番用）を用います。Paper Trading は別 DB を使う点に留意してください。
- OpenAI API 呼び出しはネットワーク/429/5xx に対してリトライ実装がありますが、APIキー未設定時は例外を投げます。
- プロセス優先度や CPU affinity の設定はプラットフォームに依存し、権限不足時は警告となります。

ディレクトリ構成（主要ファイル / モジュール）
----------------------------------------
src/kabusys/
- __init__.py                 — パッケージ定義（__version__ 等）
- config.py                   — 環境変数 / 設定管理（.env ロード、Settings クラス）
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor 単体起動スクリプト

サブパッケージ / 主要モジュール
- ai/
  - news_nlp.py               — ニュースの NLP（OpenAI）によるスコアリング
  - regime_detector.py        — 市場レジーム判定（ETF + マクロニュース + LLM）
- monitoring/
  - monitoring_db.py          — SQLite 監視DB 層（スキーマ初期化 + MonitoringDB クラス）
  - system_monitor.py         — システム・データ鮮度監視
  - trade_monitor.py          — 注文滞留 / 約定異常監視
  - risk_monitor.py           — ドローダウン / ポジション上限監視
  - kill_switch.py            — kill.flag を用いた停止シグナル
  - alert_manager.py          — LINE Push 通知ラッパー
  - monitoring_engine.py      — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py    — Streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py             — 起動時の注文・ポジションリコンシリエーション
  - order_manager.py          — 注文管理（状態遷移・送信）
  - (その他の execution モジュール：broker_factory, execution_engine, order_repository 等が参照されます)
- portfolio/
  - portfolio_builder.py      — 候補選定 / 重み計算
  - position_sizing.py        — 発注株数計算 / リスク制限 / 単元丸め
  - risk_adjustment.py        — セクターキャップ / レジーム乗数
- research/
  - factor_research.py        — モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- utils/
  - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ

付録（便利なコマンド例）
-----------------------
- Monitoring 起動（60秒間隔）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
本 README はコードベースの説明に特化しています。実際のプロジェクトで配布する場合は LICENSE ファイルや開発者向け CONTRIBUTING 指針を追加してください。

問い合わせ
----------
実装上の詳細や使用方法で不明点があれば、該当モジュールのドキュメントコメント（docstring）を参照してください。さらに情報が必要なら具体的な用途（例: 実行環境、利用したい機能、発生しているエラー）を添えて質問してください。