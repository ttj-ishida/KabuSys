# KabuSys

日本株向け自動売買（バックテスト / 実運用補助）ライブラリ群の一部です。本リポジトリには、監視・実行・ポートフォリオ構築・リサーチ・AI支援（ニュースセンチメント / レジーム判定）などのコンポーネントが含まれます。

以下はコードベースの概要、機能一覧、セットアップおよび使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引を支援するためのモジュール群です。本リポジトリでは主に次の責務を持つコンポーネントを提供します。

- Execution: ブローカーとのやり取り、注文管理、再同期（Reconciler）などの発注ロジック
- Monitoring: システム状態・注文状態・リスクの監視、アラート送信、kill-switch
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限等のポートフォリオ構築ロジック
- Research: ファクター計算（モメンタム／バリュー／ボラティリティ等）、IC計算、将来リターン計算
- AI: ニュース記事のセンチメント評価（OpenAI）や市場レジーム判定
- Tools: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード等
- Utils / Config: 環境変数パーサ、プロセス優先度設定等のユーティリティ

設計上、DB（SQLite / DuckDB）を使った永続化と、外部 API（ブローカー・OpenAI）／LINE通知等との連携を想定しています。Paper Trading（検証用）と Live（本番）を分離して運用できるように設計されています。

---

## 主な機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス生存 / データ鮮度）
- 注文滞留検出、約定価格の異常検出（TradeMonitor）
- ドローダウン・ポジション上限監視（RiskMonitor）＋ kill.flag による ExecutionEngine 停止シグナル
- LINE による監視アラート（AlertManager）
- Streamlit ダッシュボード（監視データの可視化）
- ExecutionEngine 起動 / ブローカークライアント切替（本番 vs paper_trading）
- Reconciler による起動時の注文・ポジション同期
- Portfolio construction（候補選定、等重／スコア重み、リスクベースのポジション決定）
- Research 用ファクター計算（momentum / value / volatility）と特徴量解析ユーティリティ
- ニュース記事を LLM（OpenAI）でスコアリングして ai_scores テーブルに書き込む処理
- 市場レジーム判定（ETF MA + LLM マクロセンチメントの合成）
- Paper Trading 検証レポート生成ツール

---

## セットアップ手順（開発 / 実行環境）

1. Python の準備
   - 推奨: Python 3.10+（コードは型ヒントや標準ライブラリの近年機能を使用）
   - 仮想環境の作成と有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 本リポジトリに requirements.txt がない場合は、少なくとも以下をインストールしてください:
     - pip install duckdb psutil openai requests streamlit
   - 実際のプロダクション向けにはブローカー SDK や追加パッケージが必要になる場合があります。

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS環境変数が優先）。
   - 自動ロードを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE = instant | partial | never | reject
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

4. データディレクトリ
   - デフォルトでは `data/` 下に DB や pid/flag が作成されます。必要に応じてパスを環境変数で変更してください。

---

## 使い方（主要スクリプト・API）

以下はプロジェクト内の実行用エントリポイントの使い方例です。

1. 監視ループ起動（Monitoring）
   - 標準的な起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - run_monitoring は Settings に従って sqlite/duckdb を接続し、監視ループを実行します。
   - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは共通 DB）。

2. 実行エンジン起動（ExecutionEngine）
   - Paper Trading（検証）で起動:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - この場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ保存され、実運用 DB と分離されます。
   - Live/Development:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - 実行時はプロセス優先度を High に設定する処理が最初に走ります（プラットフォームに依存）。

3. Paper Trading 検証レポート
   - コマンドラインツール:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from YYYY-MM-DD（開始日）
     - --to YYYY-MM-DD（終了日）
     - --db PATH（SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）などを標準出力に表示し PASS/FAIL を判定します。

4. Streamlit ダッシュボード（監視）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで監視ダッシュボード（Overview / Positions / Orders / System）を表示します（DB は read-only で開きます）。

5. AI 関連（プログラム API）
   - ニューススコアリング（ai/news_nlp.py）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=None)  # api_key が None の場合は環境変数 OPENAI_API_KEY を使用
   - レジーム判定（ai/regime_detector.py）:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)

6. 監視 / アラートのカスタマイズ
   - AlertManager（LINE通知）を使う場合は Settings の LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定してください。
   - KillSwitch は RiskMonitor の出力に応じて kill.flag を書き、ExecutionEngine 側でこれを観測して停止する仕組みです（ExecutionEngine が kill.flag を監視する実装を持つ前提）。

---

## 重要な設定・挙動メモ

- 環境（KABUSYS_ENV）
  - 開発用: "development"
  - 検証用（Paper Trading）: "paper_trading"
  - 本番: "live"
  - Settings は不正値で例外を投げます。

- Paper Trading の挙動
  - KABUSYS_ENV=paper_trading のとき、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。

- DB 初期化
  - run_monitoring / run_execution の起動で監視用 SQLite テーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成・マイグレーションします（init_monitoring_db）。

- プロセス優先度・CPU affinity
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます（psutil を使用、権限不足時は警告を出して続行）。

- kill.flag
  - KillSwitch はファイル（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止を促します。既存ファイルがある場合は再書き込みしません（冪等）。Settings.kill_flag_clear_on_start を用意しています（ExecutionEngine 起動時にクリアする用途）。

---

## ディレクトリ構成（主要ファイル）

概略:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env の読み込みと Settings クラス
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト（paper_trading に対応）
  - utils/
    - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化と永続化 API（MonitoringDB）
    - system_monitor.py          — CPU/メモリ/プロセス/data freshness 監視
    - trade_monitor.py           — 注文滞留・約定異常チェック
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — kill.flag 書き込みユーティリティ
    - alert_manager.py           — LINE 通知ユーティリティ
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py     — Streamlit ダッシュボード
  - execution/
    - order_manager.py           — 注文作成/送信/キャンセル等の上位 API
    - reconciler.py              — 再起動時の注文・ポジション同期
    - (その他: broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py       — 候補選定 / 重み付け
    - position_sizing.py         — 株数決定・スケールダウンロジック
    - risk_adjustment.py         — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py         — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                — ニュースを LLM でスコアリングして ai_scores へ書込
    - regime_detector.py         — ETF MA + マクロ NLP によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

データファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag

---

## 開発上の注意事項 / 推奨運用

- .env の管理:
  - .env.example をベースに .env を作成して運用。機密情報は .env.local や環境管理システムで管理してください。
- OpenAI API:
  - ai モジュールは OPENAI_API_KEY を必要とします。API制限やコストに注意してください。API 呼び出しはリトライとバックオフを組み込んでいますが、失敗時にはフェイルセーフ（スコア 0 等）で継続する設計です。
- DB のバックアップ・権限:
  - 監視ログ・取引ログは重要です。適切なバックアップとアクセス権限管理を行ってください。
- テスト:
  - OpenAI 呼び出しや psutil 系はテストで差し替え（モック）を行うことを想定しています（コード内で patch しやすい設計）。

---

README では主要な利用方法をまとめました。詳細な API リファレンスや ExecutionEngine / Broker 実装、Strategy の具体的なアルゴリズムは各モジュールの docstring および別途ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であれば README に追記すべき具体項目（例: ブローカー設定方法や tests 実行手順）を教えてください。