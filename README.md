KabuSys — 日本株自動売買システム（抜粋）
====================================

このリポジトリは日本株自動売買システム KabuSys の主要コンポーネント群（監視、実行エンジン、ポートフォリオ構築、リサーチ、AI 補助など）の実装を含みます。本 README はコードベース（src/kabusys）を元に、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を簡潔にまとめたものです。

プロジェクト概要
---------------
- 目的: 日本株を対象としたアルゴリズム売買プラットフォームのコアコンポーネントを提供する。
- 主な責務:
  - ExecutionEngine: 注文作成・発注・リスク管理・リコンシリエーション
  - MonitoringEngine: システム稼働・注文件数・リスク（ドローダウン等）の継続監視とアラート
  - Portfolio モジュール: 候補選定、配分、ポジションサイズ計算、セクター制約適用
  - Research モジュール: ファクター計算、将来リターン、IC・統計解析
  - AI モジュール: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
  - ツール: Paper Trading の検証レポート生成など

主な機能一覧
-------------
- 監視（monitoring）
  - CPU / メモリ / ディスク使用率の記録
  - Execution プロセスの生存監視（PID ファイルチェック）
  - データ鮮度チェック（price データの最終日）
  - 注文滞留・約定異常の検出と risk_logs への記録
  - ドローダウンやポジション上限監視、kill.flag による停止要求
  - LINE 通知（AlertManager：トークン未設定時はログ出力）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を閲覧）
- 実行（execution）
  - Broker クライアントの抽象化（paper_trading では MockBrokerClient を使用）
  - OrderManager による注文ライフサイクル管理（重複検出や状態同期）
  - Reconciler による起動時の自動復旧・突合せ
  - RiskManager 等による発注前チェック（制限率・利用率など）
- ポートフォリオ構築（portfolio）
  - シグナルから候補選定、等重・スコア重み付け、リスク調整（セクター制限・レジーム乗数）
  - ポジションサイズ計算（ロット丸め、aggregate cap、コストバッファ）
- リサーチ（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL 実装）
  - 将来リターン計算、IC（Spearman）やファクター要約統計
- AI（ai）
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルに保存
  - 市場レジーム判定（ETF MA とマクロ記事の LLM 評価を合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

セットアップ手順（ローカル開発向け）
---------------------------------
1. Python 環境
   - Python 3.10+ を推奨（コードは型ヒントに union 型等を使用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

2. 依存ライブラリ（最低限）
   - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトの requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. 環境変数 / .env
   - 自動ロード: src/kabusys/config.py はプロジェクトルートを .git または pyproject.toml から自動検出し、
     .env（既存の OS 環境変数を上書きしない）→ .env.local（上書き）を自動で読み込みます。
     自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数（サンプル）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=... (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN=... (アラート送信)
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (監視ループ間隔秒)
   - .env の記法は shell 形式（export を許容）、クォートやコメント行に対応します。

4. データディレクトリ
   - デフォルトで data/ 以下を使用します。必要に応じて作成:
     - mkdir -p data

使い方（主要エントリポイント）
-----------------------------
- 監視ループ（システム監視）
  - 実行：
    - python -m kabusys.run_monitoring
  - 動作:
    - Settings.sqlite_path（デフォルト data/monitoring.db）へ接続し監視テーブルを初期化
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
    - 停止: プロセスは data/stop_requested.flag を検知するとループを終了します

- 実行エンジン（Execution）
  - 実行：
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=development|live python -m kabusys.run_execution
  - 動作:
    - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db（デフォルト）に完全分離して記録
    - start 時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書き込み、stop は data/stop_requested.flag の作成や kill.flag に依存

- Streamlit ダッシュボード（監視 UI）
  - 起動：
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で monitoring DB を開き、Positions / Orders / System / Overview を表示

- Paper Trading 検証レポート
  - 実行：
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用
  - 出力: 指定期間の稼働率・注文成功率・送信率・レイテンシ等を算出して PASS/FAIL 判定を表示

- AI / リサーチ関数の直接利用（Python REPL など）
  - ニューススコアリング（例）:
    - from datetime import date
      import duckdb
      from kabusys.ai import score_news
      conn = duckdb.connect('data/kabusys.duckdb')
      score_news(conn, date(2026,4,10), api_key='YOUR_OPENAI_KEY')
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, date(2026,4,10), api_key='YOUR_OPENAI_KEY')

停止フロー（フラグファイル）
-------------------------
- 停止要求（run_monitoring / run_execution 共通）
  - data/stop_requested.flag の存在を起点に両プロセスは停止処理を行います（run_monitoring はループを抜ける）。
- Kill switch（システムが致命的なリスクを検出した場合）
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止を要求します。
  - ExecutionEngine 側は Settings.kill_flag_path（デフォルト data/kill.flag）でチェックします。
  - KillSwitch.clear() でフラグを削除できます（起動時に消去する設定もあります）。

重要な設定・挙動
----------------
- 環境切り替え:
  - KABUSYS_ENV は development / paper_trading / live のいずれか。paper_trading は実口座と DB を完全分離。
- Paper Trading の注文約定動作:
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御（instant / partial / never / reject）。
- 自動 .env ロード:
  - プロジェクトルート（.git か pyproject.toml 基準）から .env と .env.local を自動読み込みします（既存 OS 変数は保護）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil に依存、権限不足時は警告出力）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- kabusys/
  - __init__.py              — パッケージ基本情報
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py        — SystemMonitor ポーリングループの起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄別スコア化
    - regime_detector.py     — 市場レジーム判定（MA + マクロ記事 LLM）
  - monitoring/
    - monitoring_db.py       — SQLite 監視ログのスキーマ・永続化
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成 / 判定
    - alert_manager.py       — LINE API によるアラート送信
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit デバッグダッシュボード
  - execution/
    - order_manager.py       — 注文ライフサイクル管理
    - reconciler.py          — 起動時のリコンシリエーション
    - (その他 broker_factory 等の実装を参照)
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・キャップ・スケール調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計ユーティリティ
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

開発メモ / 注意点
-----------------
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時に冪等的にテーブルを作成し、いくつかの軽微なマイグレーション（カラム追加）を行います。
- DuckDB を使ったリサーチ系関数は prices_daily / raw_financials / raw_news 等のテーブルを前提としています。データ投入は別途データパイプライン（kabusys.data.pipeline）を用意してください。
- OpenAI 呼び出しは外部ネットワークに依存するため、API キー管理とレート制御に注意してください。API エラー時は多くの箇所でフォールバック（0 やスキップ）する実装になっています。
- 実運用では KABUSYS_ENV=live の下で KABU_API_PASSWORD 等正しい設定が必要です。実戦投入は十分な検証のうえ行ってください（本コードは教育・研究用途の参照実装です）。

ライセンス・貢献
----------------
- 本 README はコードベースの抜粋に基づく説明です。実際のライセンス・貢献ポリシーはリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください（本抜粋には含まれていません）。

問い合わせ
---------
- 実行上の不明点や初期化手順については、該当モジュール（config.py、run_* スクリプト、monitoring/ 内のログ出力）を確認してください。必要であれば具体的な環境変数やエラー例を添えて質問してください。

--- 
必要であれば、README に含めるサンプル .env や具体的な CLI 実行例（環境変数の完全例）を追記します。どの情報をより詳しく載せたいか教えてください。