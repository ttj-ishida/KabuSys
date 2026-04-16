# KabuSys

KabuSys は日本株の自動売買プラットフォーム（プロトタイプ）です。  
本リポジトリは以下の主要コンポーネントを含みます：

- Execution Engine（発注/管理、リスク管理、リコンシリエーション）
- Monitoring（システム監視、トレード監視、リスク監視、アラート）
- Research（ファクター計算、特徴量解析）
- AI（ニュースセンチメント、レジーム判定：OpenAI を利用）
- Portfolio（銘柄選定・配分・ポジションサイジング）
- Tools（Paper Trading の検証レポート等）
- Streamlit ダッシュボード（監視用 UI）

以下にプロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を示します。

---

## プロジェクト概要

KabuSys はバックエンド中心の自動売買システムで、実運用と Paper Trading（検証環境）を分離して扱います。  
監視コンポーネントは発注エンジンの稼働状況やデータ鮮度、滞留注文、約定異常、ドローダウン等をチェックし、必要に応じてアラート送信や停止フラグ発行（kill flag）を行います。OpenAI API を使ったニュースセンチメントとマクロセンチメントを活用して市場レジーム判定やニューススコアリングを行えます。

---

## 主な機能一覧

- Execution
  - 発注管理（OrderManager）
  - ブローカー抽象化（BrokerClientFactory を通して実運用 / モックを切替）
  - リスク管理（RiskManager）
  - リコンシリエーション（Reconciler）による再起動時の自動同期
  - Paper Trading モード（本番 DB と完全分離、data/paper_trading.db）

- Monitoring
  - システム状態収集（CPU/Memory/Disk、Execution プロセスの生存確認）
  - データ鮮度チェック（DuckDB 上の価格データ最終日）
  - 注文滞留・約定異常の検出
  - ドローダウン／ポジション数監視（KillSwitch による停止判定）
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）評価
  - 候補選定、等重・スコア加重配分、リスク調整、ポジションサイジング

- AI
  - ニュースのセンチメント解析（OpenAI：gpt-4o-mini を想定）
  - マクロニュース＋ETF の MA200 乖離で市場レジーム判定
  - 扱いはフェイルセーフ（API 失敗時は中立として継続）

- Tools
  - Paper Trading の検証レポート生成スクリプト（稼働率・成功率・レイテンシ等を集計）

---

## セットアップ手順（開発環境向け）

※下記はリポジトリルートで実行することを想定しています。パッケージ化/インストール済みであれば PYTHONPATH 指定は不要です。

1. Python 環境
   - Python 3.10+ を推奨（typing の一部構文を利用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて）pytest 等
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. ソースを PYTHONPATH に読み込ませる
   - プロジェクトルートに `src/` があるレイアウトを想定しています。
   - 実行時に以下のようにするか、編集してインストール:
     - PYTHONPATH=src python -m kabusys.run_monitoring
   - 開発時は pip editable install:
     - pip install -e .

4. データディレクトリ作成
   - data ディレクトリと DB 初期ファイル（存在しなければ自動生成されることが多いですが、手動で作る場合）
     - mkdir -p data

5. 環境変数 / .env
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数優先）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主なもの）

Settings クラスで参照される主要な環境変数（一部とデフォルト）:

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用（未設定時は送信しない）
- PAPER_FILL_MODE: paper trading の約定挙動（instant / partial / never / reject） — default "instant"
- PAPER_TRADING_SQLITE_PATH: Paper Trade 用 SQLite（default: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB（分析用）ファイルパス（default: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視/停止制御）

細かい挙動や検証は `src/kabusys/config.py` を参照してください。

---

## 使い方（実行コマンド例）

注意: src ディレクトリを PYTHONPATH に含めるか、パッケージをインストールしてください。

- Monitoring（常駐の監視プロセス）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - export MONITOR_POLL_INTERVAL=30  # 秒（1 秒以上）
  - 監視は常に本番の sqlite_path を使用します（環境にかかわらず）。

- Execution Engine（発注エンジン）
  - PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、Paper Trading DB を利用します:
    - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution

- Streamlit ダッシュボード（監視UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Dash は監視 DB を読み取り専用で開きます（DB が無ければエラー表示）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH で既定の DB を指定可能

- AI 機能（ライブラリ呼び出し）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止 / フラグ
  - プロセスを外部から停止させたい場合は以下ファイルを作成します（KillSwitch / run scripts が検知）:
    - data/stop_requested.flag — run_monitoring / run_execution が検知して終了するためのフラグ
    - data/kill.flag — ExecutionEngine に停止を要求するための kill フラグ（KillSwitch が作成）
  - ExecutionEngine の PID ファイル: data/execution.pid（存在確認・stale PID 検出などに利用）

---

## 監視（Monitoring）に関する主なポイント

- Monitoring は SQLite（monitoring.db）へ各種ログを永続化します。初回起動時にテーブルを作成します（冪等）。
- Monitoring の構成要素:
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス生存、データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: RiskMonitor のルールに基づいて kill.flag を書き込み、Execution を停止させる
  - AlertManager: LINE push で通知（トークン未設定時はログ出力のみ）
- Streamlit ダッシュボードは monitoring.db を読み取り専用で表示します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — 環境変数/設定読み込みロジック（.env 自動ロード）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI 呼び出し）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — monitoring 用 SQLite 永続層（init, MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 複数モニタ束ねる実行ロジック
  - streamlit_dashboard.py — Streamlit UI
- execution/
  - reconciler.py — 起動時の自動同期ロジック
  - order_manager.py — 発注関連 API（State Machine）
  - order_repository.py（DB）、order_record.py（状態列挙 等）など（実装の一部）
  - broker_factory / broker_api — ブローカー抽象化
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（フルツリーや追加モジュールは実際のリポジトリを参照してください）

---

## 開発上の注意点 / 実運用上の注意

- env による挙動差分:
  - KABUSYS_ENV=paper_trading の場合、Paper 用 DB を使い実運用 DB と分離して動作します（Mock ブローカー等）。
  - Monitoring の監視ログは環境にかかわらず本番 sqlite_path を使う実装箇所があるため、運用時は注意してください（コード内に注記あり）。
- OpenAI 呼び出しは課金やレート制限の対象です。API キー管理・リトライ/バックオフの挙動は各モジュールで実装されていますが、運用前に十分確認してください。
- プロセス優先度や CPU affinity の設定は psutil に依存します。権限不足で失敗する可能性があるためログでスキップされます。
- DB マイグレーションは簡易的なチェック + ALTER TABLE による追記を行っています。大きなスキーマ変更時は注意してください。
- 本リポジトリは実運用システムのプロトタイプ的構成です。実運用では追加の安全弁、監査ログ、テスト、検証が必要です。

---

## よく使うコード / 呼び出し例

- Monitoring を一回だけ実行（テスト用）:
  - from kabusys.monitoring.monitoring_engine import MonitoringEngine
  - エンジンの run_once() を使って単発チェックが可能

- Research の関数呼び出し例:
  - from kabusys.research import calc_momentum, calc_volatility
  - calc_momentum(duckdb_conn, date(2026, 4, 1))

- AI スコア書き込み（ニュース）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, date.today(), api_key="...")

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring（src 以下の各 .py）を参照してください。運用・拡張の際はまずテスト環境（paper_trading）で動作確認を行ってください。