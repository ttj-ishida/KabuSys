README
======

このドキュメントは、KabuSys（日本株自動売買システム）のコードベースに対する簡易 README です。プロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買システムおよび監視/研究ツール群です。本リポジトリは以下の役割を持つ主要コンポーネントで構成されます。

- ExecutionEngine：ブローカーへの発注・注文管理・リスク管理・再同期（リコンシリエーション）などの取引実行ロジック
- Monitoring：システム稼働状況、注文の滞留や約定異常、ドローダウン等を監視し、ログ化・通知・キルスイッチ制御を行う
- Research：DuckDB 上の株価・財務データを用いたファクター計算、将来リターン・IC 計算などの解析ツール
- AI：ニュース文書を LLM（OpenAI）でスコアリングして銘柄ごとのセンチメントを算出、マーケットレジーム判定など
- Tools：Paper Trading の検証レポート生成などのユーティリティスクリプト

特徴・機能一覧
---------------
- 実行/監視
  - run_execution.py：ExecutionEngine 起動スクリプト（本番 / paper_trading を切替可能）
  - run_monitoring.py：SystemMonitor ポーリングループ（SNMP 等ではなく SQLite にログ保存）
  - stop / kill 用のフラグファイル連携（data/stop_requested.flag, data/kill.flag）
- 監視機能
  - system_monitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度を監視しログを記録
  - trade_monitor：滞留注文・約定異常価格検出
  - risk_monitor：ドローダウン・ポジション上限を監視してリスクイベントを記録
  - alert_manager：LINE Messaging API を使った通知（クールダウン管理付き）
  - streamlit_dashboard：監視データを可視化するダッシュボード（Streamlit）
- 発注・リスク管理
  - OrderManager / OrderRepository / Reconciler：注文状態管理、再起動時の同期（ブローカー照合）
  - RiskManager：発注前のリスクチェック（設定に基づく）
- ポートフォリオ構築（純関数）
  - 候補選定、等配分/スコア加重配分、セクター上限適用、ポジションサイズ算出（単元丸め・集約上限・スケーリング）
- 研究・解析
  - factor_research：Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（Spearman）計算、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news：ニューステキストを LLM に投げて銘柄別スコアを ai_scores テーブルに書き込み
  - regime_detector.score_regime：ETF (1321) の MA とマクロニュースの LLM スコアを合成して market_regime テーブルに保存
- ユーティリティ
  - process_priority：プラットフォーム抽象化されたプロセス優先度 / CPU affinity 設定
  - tools.paper_verification_report：Paper Trading 用検証レポート生成（稼働率・注文成功率・レイテンシ等）

前提条件
--------
- Python 3.9+ 推奨（型注釈に基づく）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリで使用）
- ブローカー API 用の実装は本コードベース内で抽象化されている（BrokerClientFactory 等）

セットアップ手順
----------------
1. リポジトリをクローン／取得し、作業ディレクトリをプロジェクトルートにする（pyproject.toml または .git がある場所）。
2. 仮想環境を作成・有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit
   - （実環境では requirements.txt を用意して pip install -r requirements.txt を推奨）
4. 環境変数を設定する:
   - .env / .env.local に設定するか、OS 環境変数として設定する。
   - 自動 .env 読み込みはデフォルトで有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. データディレクトリを作成（任意だがデフォルトパスを使う場合）:
   - mkdir -p data

主な環境変数（主なもの）
-----------------------
（左: 変数名 — 役割 / デフォルト値）
- KABUSYS_ENV — 環境モード（development | paper_trading | live） デフォルト: development
  - paper_trading の場合、run_execution は MockBrokerClient を使い data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知のため（未設定なら通知はスキップ）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject） デフォルト: instant
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（よく使うコマンド）
------------------------

前提: python の import path に src が含まれているか、パッケージをインストール済みであること。
（開発時: プロジェクトルートで PYTHONPATH=src python -m kabusys.run_monitoring のように実行）

1) 監視プロセス（SystemMonitor のポーリング）を起動
   - 簡易実行:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL をオーバーライド:
     - MONITOR_POLL_INTERVAL=120 PYTHONPATH=src python -m kabusys.run_monitoring
   - 説明:
     - スクリプトはプロセス優先度を high に設定し、SQLite（settings.sqlite_path）へ監視ログを書きます。
     - 停止は data/stop_requested.flag を作成することで検知して終了します。

2) 実行エンジン（ExecutionEngine）を起動
   - 本番/開発/ペーパートレードは KABUSYS_ENV で切替:
     - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
     - KABUSYS_ENV=live PYTHONPATH=src python -m kabusys.run_execution
   - 説明:
     - paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH に記録され本番 DB と分離されます。
     - 実行中に data/stop_requested.flag が存在するとエンジンを停止します。

3) Paper Trading 検証レポートを生成
   - 例:
     - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - デフォルト DB は data/paper_trading.db。別 DB を使う場合は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を指定。
   - 出力:
     - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを標準出力に表示します。

4) Streamlit 監視ダッシュボードを起動
   - 例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - SQLite を読み取り専用で開き、ポートフォリオダッシュボード・ポジション・注文・システムステータス・リスクログを表示します。

5) AI モジュール（ニューススコアリング / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要。
   - Python REPL やスクリプトから呼び出し:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - いずれも DuckDB 接続と target_date（datetime.date）を渡して使用します。
   - 例（概念）:
     - import duckdb, datetime
       conn = duckdb.connect("data/kabusys.duckdb")
       score_news(conn, datetime.date(2026,4,1), api_key="sk-...")
   - 注意:
     - テーブル構造（raw_news / news_symbols / ai_scores / prices_daily / market_regime）が前提条件です。
     - API リクエストはリトライ・バックオフ等の頑健性が実装されていますが、API 制限に注意してください。

停止・フラグファイル
-------------------
- 停止要求（外部からの安全停止）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して順次停止します。
- 強制停止（Kill Switch）
  - KillSwitch が判定したときに data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグがあれば起動を中止します。
  - KillSwitch の理由はファイルに書き込まれます。clear() で削除できます。

設定読み込みのしくみ
--------------------
- 自動で .env / .env.local の順に読み込みます（ただし OS 環境変数は保護される）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースはシェルの export KEY=val 形式とシンプルなコメント処理に対応します。

ディレクトリ構成（主要ファイル・モジュール）
-----------------------------------------
（src/kabusys をルートとする主要モジュール）

- src/kabusys/
  - __init__.py                       — パッケージ定義、バージョン
  - config.py                         — Settings / 環境変数読み込みロジック
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py                — SQLite 用永続化層（初期化 + MonitoringDB クラス）
    - system_monitor.py               — システムチェック（CPU/メモリ/プロセス/データ鮮度）
    - trade_monitor.py                — 注文監視（滞留/約定異常）
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - kill_switch.py                  — kill.flag 書き込みユーティリティ
    - alert_manager.py                — LINE 通知送信（クールダウン管理）
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py                — 発注フロー（OrderManager）
    - reconciler.py                   — 起動時の再同期ロジック
    - order_repository.py             — Orders DB 操作（別ファイル想定）
    - ...（Broker API 抽象化、ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py            — 候補選定 / 重み計算
    - position_sizing.py              — 株数決定・集約上限処理
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py              — マーケットレジーム判定（OpenAI + MA）
  - data/                              — 実行時に生成されることが期待されるディレクトリ（例: monitoring.db, kabusys.duckdb, pid, flag）

注意事項 / 運用メモ
------------------
- run_monitoring / run_execution は起動時にプロセス優先度を "high" に設定しようとします。psutil の権限によっては設定に失敗する場合があり、その場合は警告が出力されます。
- Paper Trading モードは本番 DB と完全に分離するよう設計されていますが、環境変数の設定ミスに注意してください。
- DuckDB テーブルスキーマ（prices_daily, raw_financials, raw_news など）は想定された形で用意されている必要があります。AI 機能や研究機能はこれらのテーブルを前提に動作します。
- OpenAI API 呼び出しを行う機能は外部 API の利用料金・レート制限の影響を受けます。API キーの管理・リトライ挙動の理解を運用上確認してください。
- SQLite / DuckDB ファイルのバックアップや排他アクセス（複数プロセスからの書き込み）の運用設計に注意してください。streamlit ダッシュボードは監視 DB を read-only で開くことを推奨しています（実装済み）。

問い合わせ・拡張
-----------------
- 追加機能や外部 Broker の実装、CI 用の要件、運用監視ルール等が必要な場合は、該当するモジュール（execution/*.py, monitoring/*.py）を参照して拡張してください。
- テストを書く際は Settings の自動 .env 読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化すると便利です。

以上が本リポジトリの概要、セットアップ、及び基本的な使い方です。必要に応じて README に実行例や運用手順（systemd ユニットや Docker Compose などのサービス化）を追記してください。