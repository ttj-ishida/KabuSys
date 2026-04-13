KabuSys — README
===============

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群です。本リポジトリは以下の主要機能を持つモジュールを含みます。

- 実行系（ExecutionEngine）: ブローカーへの発注・状態管理・リスク制御・再同期（reconciliation）
- 監視系（MonitoringEngine）: システム状態、注文滞留、ドローダウン等の定期チェックとログ化、LINE 通知、KillSwitch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ適用
- リサーチ（Research）: ファクター計算（Momentum / Value / Volatility）、IC 計算、特徴量解析
- AI ユーティリティ: ニュースセンチメント（OpenAI を利用）と市場レジーム判定
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード

主な設計方針
- 本番環境と paper_trading（検証）環境の分離（SQLite DB を別ファイルで管理）
- ルックアヘッドバイアスに配慮（datetime.today() を直接参照しない等）
- 外部 API 呼び出し時はリトライ制御・フェイルセーフを実装
- 多くのコンポーネントは純粋関数または DB 操作に限定（テスト容易性）

機能一覧
--------
- 実行/再同期
  - OrderManager, Reconciler による発注/同期処理
  - BrokerClientFactory 経由で実ブローカー or MockBroker を切り替え
- 監視/アラート
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件に応じてフラグファイルを書き ExecutionEngine を停止
  - Streamlit ダッシュボードで最小限の UI 提供
- ポートフォリオ
  - 候補選定（スコア順）、等重・スコア加重、リスクベースサイズ決定、セクター制限
- リサーチ
  - DuckDB 経由で prices_daily / raw_financials を参照しファクター計算
  - forward return / IC / ファクター統計
- AI
  - OpenAI（gpt-4o-mini）でニュースをスコアリングし ai_scores として保存
  - マクロニュース + ETF ma200 に基づく市場レジーム判定
- 運用ツール
  - paper_verification_report: paper_trading のログから検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.9+（typing / 型注釈に依存）
- 必要な外部ライブラリ: duckdb, psutil, requests, openai, streamlit など

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - （プロジェクトに requirements.txt がある場合）pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 主な環境変数（デフォルト / 必須）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合は必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視ログ用、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - PID_FILE_PATH: data/execution.pid（デフォルト）
     - KILL_FLAG_PATH: data/kill.flag（デフォルト）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

4. データディレクトリ作成
   - mkdir -p data

使い方（実行例）
----------------

1) 監視ループを起動（SystemMonitor 単体でポーリング）
- 環境変数 MONITOR_POLL_INTERVAL で間隔を秒指定（デフォルト 60 秒）
- 実行:
  - python -m kabusys.run_monitoring

2) ExecutionEngine を起動（発注処理）
- 本番モード:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading（モックブローカーを使い data/paper_trading.db に記録）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - PAPER_FILL_MODE を設定して約定挙動を調整（例: PAPER_FILL_MODE=partial）

3) Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- DB が存在しない場合は MonitoringEngine を先に起動してください。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI 機能（ライブラリ API として利用）
- ニューススコア付与:
  - Python REPL / スクリプトから duckdb 接続を渡して呼び出す:
    - from openai import OpenAI
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, datetime.date(2026,4,10), api_key="YOUR_OPENAI_KEY")
- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, datetime.date(2026,4,10), api_key="YOUR_OPENAI_KEY")

設定・挙動の補足
----------------
- Settings（kabusys.config）により .env / .env.local を自動読み込みします（プロジェクトルートは .git / pyproject.toml を基準に検出）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- monitoring は KABUSYS_ENV に関わらず監視用の sqlite_path（デフォルト data/monitoring.db）を使用します。
- paper_trading モードは発注・ログを本番 DB と分離します（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度は起動時に set_process_priority("high") が呼ばれます（psutil を用いるため権限によっては警告が出ます）。

ディレクトリ構成（主要ファイル）
----------------------------
- src/kabusys/
  - __init__.py                          — パッケージ定義 / バージョン
  - config.py                            — 環境変数 / 設定管理（.env ロード・Settings）
  - run_monitoring.py                    — SystemMonitor のポーリング起動スクリプト
  - run_execution.py                     — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py                — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                   — SQLite ベースの監視ログ層（スキーマ初期化・CRUD）
    - system_monitor.py                  — システム状態・データ鮮度監視
    - trade_monitor.py                   — 注文滞留・約定異常監視
    - risk_monitor.py                    — ドローダウン・ポジション上限監視
    - kill_switch.py                     — kill.flag 書き込みロジック
    - alert_manager.py                   — LINE push 通知（クールダウン管理）
    - monitoring_engine.py               — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py             — Streamlit ベースの簡易ダッシュボード
  - execution/
    - order_manager.py                   — 発注制御（Order State Machine）
    - reconciler.py                      — 起動時の自動復旧 / ポジション照合
    - order_repository.py                 — Orders DB（別ファイル想定）
    - ...（ブローカー API / factory 等）
  - portfolio/
    - portfolio_builder.py               — 候補選定・重み計算
    - position_sizing.py                 — 株数決定・単元丸め・キャップ
    - risk_adjustment.py                 — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py                 — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py             — 将来リターン / IC / 統計ユーティリティ
    - __init__.py
  - ai/
    - news_nlp.py                        — OpenAI を使ったニュースセンチメントスコアリング
    - regime_detector.py                 — ETF MA + マクロセンチメントでレジーム判定
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py       — paper_trading 検証レポート生成ツール
  - data/                                  — デフォルト DB / PID / flag を格納する想定ディレクトリ
    - kabusys.duckdb (デフォルト)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - execution.pid
    - kill.flag

開発・運用上の注意
------------------
- DB マイグレーションは monitoring_db.init_monitoring_db() が起動時に冪等的に実行します。既存 DB に新カラムがない場合は ALTER TABLE による追加を行います。
- OpenAI など外部 API キーは環境変数で管理してください。API 呼び出しで例外が発生した場合、各モジュールは可能な限りフォールバック（スコア 0.0 等）して続行します。
- 実行時のプロセス優先度・CPU affinity の設定はプラットフォーム依存で失敗することがあります（権限不足等）。失敗時は警告ログが出ますが実行自体は継続します。
- Paper Trading は本番 DB と分離設計されているため、検証中に本番データを上書きするリスクは低くなっていますが、環境変数と DB パス設定に十分注意してください。

貢献や拡張
----------
- ブローカークライアントの追加、注文状態遷移の補完（Closed への遷移など）、銘柄ごとの lot_size 対応、AI 評価のプロンプト改善やモデル切替は想定される拡張点です。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）に合わせて research / ai モジュールを拡張できます。

問い合わせ
----------
コード内の docstring とログメッセージを参照してください。不明点があれば該当モジュールの説明（ファイル先頭の docstring）を確認してください。

（以上）