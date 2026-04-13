# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群を含むリポジトリ（モジュール名: `kabusys`）。  
この README はコードベース（src/kabusys）に基づく簡易ドキュメントです。

---

## プロジェクト概要

KabuSys は以下の主要機能を備える自動売買プラットフォームのコンポーネント群です。

- 注文の生成・送信・状態管理（Execution）
- 発注ログ・監視イベントを保持する軽量監視 DB（Monitoring）
- ポートフォリオ構築（銘柄選定、重み付け、株数算出）
- ファクター計算・研究用ユーティリティ（Research / Factor）
- ニュースを LLM（OpenAI）でスコアリングして銘柄に紐づける機能（AI）
- 起動スクリプト・運用用ツール（監視ループ、実行エンジン、Streamlit ダッシュボード、紙トレード検証レポート）

設計上のポイント：
- 多くのロジックは純粋関数で実装され、DBアクセスは明確に分離されています。
- Paper Trading（KABUSYS_ENV=paper_trading）向けに実口座とは分離された DB を使用する設計。
- OpenAI API 呼び出しは耐障害設計（リトライ／フォールバック）を組み込んでいます。

---

## 主な機能一覧

- Execution
  - OrderManager / Reconciler による注文ライフサイクル管理と再同期
  - Broker クライアントファクトリ（本番/モック切替）
- Monitoring
  - SystemMonitor：プロセス生存・CPU/メモリ/ディスク・データ鮮度チェック
  - TradeMonitor：滞留注文検出、約定価格異常検知
  - RiskMonitor：ドローダウン／ポジション上限監視
  - KillSwitch：フラグファイルによる実行エンジン停止指示
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio
  - 候補選定、等重／スコア重み、ポジションサイズ算出、セクター上限調整、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI
  - news_nlp: raw_news を集約して OpenAI に送信・銘柄別センチメントを ai_scores に記録
  - regime_detector: ETF の MA 乖離と LLM 判定を合成して市場レジーム判定を保存
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（注文成功率・稼働率・レイテンシ等）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python >= 3.9 を想定
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール  
   リポジトリに requirements.txt がない場合は下記をインストールしてください（主要依存）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数の設定  
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数（設定必須／デフォルトを含む）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合は推奨)
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag ファイル（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: paper_trading の約定動作 ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

4. データディレクトリ作成
   - デフォルトだと data/ 以下に DB 等を置く設計です。必要に応じてディレクトリを作成してください。
     - mkdir -p data

---

## 使い方（主要スクリプト）

- 監視ループを起動（SystemMonitor 単独起動用）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定可能（デフォルト 60）
  - 実行例:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  説明:
  - プロセス優先度を high に設定し、SQLite（monitoring）と DuckDB に接続して SystemMonitor をポーリングします。
  - 監視用 DB は環境にかかわらず本番 sqlite_path を使う設計です。

- 実行エンジン起動（Execution Engine）
  - KABUSYS_ENV によって本番 / paper_trading（モックブローカー）を切替可能。
  - 実行例（Paper Trading）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行例（Live）:
    - KABUSYS_ENV=live python -m kabusys.run_execution

  説明:
  - BrokerClientFactory によりブローカークライアントを生成（paper_trading 時は MockBrokerClient）。
  - Paper Trading 用 DB は `PAPER_TRADING_SQLITE_PATH`（もしくは Settings.paper_sqlite_path）に分離されます。

- Streamlit 監視ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: read-only で monitoring DB を開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート生成
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 出力内容: 稼働率、注文成功率、送信率、レイテンシ統計、合格/不合格判定等

- AI / レジーム判定 / ニューススコア
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を直接与えて呼び出すプログラム向け API です。OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` を参照します。

---

## 主要設定（Settings クラスについて）

設定は `kabusys.config.Settings` 経由で取得します。主に環境変数ベースです。値検証・デフォルトが組み込まれています。重要なプロパティ例：

- env / is_live / is_paper / is_dev
- duckdb_path / sqlite_path / paper_sqlite_path
- pid_file_path / kill_flag_path
- paper_fill_mode（instant/partial/never/reject）
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- log_level

注意:
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出して行われます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主要ファイル・モジュールと短い説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みと Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite による永続化層（tables、MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常検出
    - risk_monitor.py — ドローダウン、ポジション数監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push 通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねるループ（テスト用 run_once/run）
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py — 注文ステートマシンの外向き API
    - reconciler.py — 起動時の注文／ポジション再同期処理
    - order_repository.py, order_record.py, broker_*.py etc.（注文関連実装）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・資金配分ロジック
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース集約 + OpenAI による銘柄別センチメント算出
    - regime_detector.py — マクロニュース + ETF MA を使ったレジーム判定
  - data/
    - pipeline.py, stats.py 等（DuckDB 関連ユーティリティ。prices_daily / raw_financials 等テーブルを扱う）

（上記は主要ファイルの抜粋です。細かなモジュールはソースツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- Paper Trading は本番 DB と完全に分離すること（`KABUSYS_ENV=paper_trading` を利用）。
- OpenAI の呼び出しは API キーとレートリミットに注意。外部 API 呼び出しはリトライやフォールバックを組み込んでいますが、コスト管理を行ってください。
- 監視処理は監視 DB（SQLite）へ書き込みます。複数プロセスでの同時書き込みやファイルバックアップに注意してください。
- PID 管理や kill.flag により ExecutionEngine の安全停止を実装しています。手動操作の際はそれらのファイルの存在を確認してください。
- Streamlit ダッシュボードは DB を読み取り専用で開くことを想定しています（起動時に読み取り専用 URI を使う）。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 監視ループ起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張してデプロイ手順、CI 設定、より詳しい設定例（.env.example）や API 使用例を追加できます。追加したい情報があれば指定してください。