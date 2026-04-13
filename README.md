# KabuSys — 日本株自動売買システム (README)

このドキュメントはこのコードベースの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめた README です。

注意: 実行にあたっては各種 API キーや DB パスなど環境変数の設定が必要です。デフォルト設定や挙動は下記に記載します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な用途は以下です。

- シグナルに基づく発注・注文管理（ExecutionEngine）
- 発注の安全性確保（リスク管理、約定リコンシリエーション）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading（本番 DB と分離して動作可能）と検証レポート生成
- DuckDB を用いたデータ分析・ファクター計算・研究用ユーティリティ
- ニュースの自然言語処理によるセンチメント評価（OpenAI を利用可能）

設計方針のポイント:
- DB は SQLite（監視・発注ログ）と DuckDB（時系列/分析用）を併用
- Paper Trading は本番 DB と分離（`KABUSYS_ENV=paper_trading`）
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ重視（API 失敗時は安全側にフォールバック）

---

## 機能一覧

- Execution
  - 起動エントリ: `kabusys.run_execution`（python -m kabusys.run_execution）
  - Broker クライアント切替（本番 / paper_trading の Mock）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine

- Monitoring
  - 起動エントリ: `kabusys.run_monitoring`（python -m kabusys.run_monitoring）
  - SystemMonitor: CPU/Memory/Disk/プロセス状態・データ鮮度を監視
  - TradeMonitor: 注文滞留・約定異常価格を監視
  - RiskMonitor: ドローダウンやポジション上限を監視しリスクイベント記録
  - KillSwitch: フラグファイルによる外部停止シグナル
  - AlertManager: LINE Messaging API による通知
  - Streamlit ダッシュボード: `monitoring/streamlit_dashboard.py`（読み取り専用で表示）

- Portfolio Construction（純粋関数群）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリー

- AI / NLP
  - news_nlp: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント集約・ai_scores書き込み
  - regime_detector: MA200 とマクロニュースの LLM評価を組み合わせた市場レジーム判定

- ユーティリティ
  - 設定管理（`.env` 自動読み込み、Settings）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - DB 初期化・マイグレーション（監視用テーブルなど）

- CLI ツール
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`

---

## 必要要件（概略）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリに含まれます）
- ネットワークアクセス（LINE / OpenAI / ブローカー API 利用時）

※ 実運用では OS の挙動差（プロセス優先度など）に注意してください。

---

## セットアップ手順（クイックガイド）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 主要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - KABUSYS_ENV: 開発モード（development | paper_trading | live）。デフォルト: development
     - `paper_trading` の場合、Mock ブローカーを使い DB は `data/paper_trading.db` を使用
   - PAPER_FILL_MODE: paper_trading の約定動作（instant / partial / never / reject）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）（デフォルト: 60）

6. DB（DuckDB / SQLite）の初期化
   - 実行スクリプトが起動時に必要テーブルを作成します（監視用テーブルは `init_monitoring_db` で冪等に作成）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番または paper_trading）
  - python -m kabusys.run_execution
  - 設定に応じて broker が選択され、ExecutionEngine がセッションを実行します。
  - 起動時にプロセス優先度を "high" に設定する処理が実行されます。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60s）。
  - 監視は常に `Settings.sqlite_path`（= 本番監視 DB）を使用します（KABUSYS_ENV に依存しない）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  - オプション `--db PATH` で SQLite ファイルを直接指定できます（優先度：--db > 環境変数 > デフォルト）。

- AI 機能（コードから呼び出し）
  - ニュースセンチメント評価:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも `api_key` を引数で渡すか環境変数 `OPENAI_API_KEY` を利用します。

備考:
- `KABUSYS_ENV=paper_trading` の場合、発注は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。本番 DB と完全分離されます。

---

## 動作上の注意点 / 運用メモ

- Settings の自動読み込み:
  - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索され、そこにある `.env` / `.env.local` を自動で読み込みます。
  - OS 環境変数は上書きされません（`.env.local` は上書き設定が可能ですが OS の環境変数は保護）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼び出します（プラットフォーム依存・権限により失敗しても警告で継続）。

- Kill Switch:
  - `KillSwitch` は `data/kill.flag`（デフォルト）を書き込むことで ExecutionEngine 停止の合図を送ります。ExecutionEngine 起動時は `Settings.kill_flag_clear_on_start` によってフラグの自動クリアを設定できます。

- DB マイグレーション:
  - `init_monitoring_db` はテーブル作成と簡易マイグレーション（カラム追加）を行います。大規模なスキーマ変更は別途対応が必要。

- フェイルセーフ:
  - OpenAI / ブローカー API の一時エラーやパースエラーは多くがフェイルセーフ（安全側のデフォルト）で処理され、例外を上位へ伝播しない設計です。ただし重要な設定未指定（API キー等）は ValueError を送出します。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings 管理（.env 自動読み込み）
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
      - order_* (その他)
    - monitoring/
      - monitoring_db.py               — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースツリーをご参照ください。）

---

## 例: 簡単な実行フロー

1. `.env` を作成し必要なキーを設定
2. DuckDB / SQLite の初期化（起動スクリプトが自動で必要テーブルを作成）
3. モニタを起動:
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
4. 本番/紙トレードの Execution を起動:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. 必要に応じて Streamlit ダッシュボードで状況を確認:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発 / テスト向けメモ

- 設定ロードを止めたいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと `.env` の自動読み込みを抑制できます。
- OpenAI 呼び出しなど外部 API はモック可能なように `_call_openai_api` や public 関数を分離しています。テストでは `unittest.mock.patch` 等で差し替えてください。
- DuckDB 接続を渡して純粋関数を直接テストできる設計になっています（副作用を最小化）。

---

この README はコードベースの主要ポイントと運用上の注意をまとめたものです。さらに詳細な設計ドキュメントや API の仕様（Broker API、OrderRecord ステートマシン、PortfolioConstruction.md 等）が別途存在する想定です。必要であれば、各サブモジュールごとの詳細ドキュメントや運用チェックリストを追加で作成できます。