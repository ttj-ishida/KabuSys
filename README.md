# KabuSys — README

以下はコードベースの簡易 README です。日本語でプロジェクトの目的、主要機能、セットアップ・実行手順、ディレクトリ構成をまとめています。

---

## プロジェクト概要
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージです。  
主な機能はシグナル→発注の実行エンジン、ポートフォリオ構築ユーティリティ、ファクター計算・研究用モジュール、AI を用いたニュース NLP、監視・アラート機能などを含みます。  
設計上、以下を重視しています：
- 本番・紙上トレード（paper trading）の分離（DB・挙動）
- ルックアヘッドバイアス回避（日時参照の設計方針）
- フェイルセーフ（API失敗時はフォールバックして継続）
- テスト容易性（純粋関数の採用、OpenAI 呼び出しの差し替え容易化）

---

## 主な機能一覧
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - ブローカークライアントの抽象化（実口座 / モック切替）
  - 注文管理（OrderManager / OrderRepository）
  - リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - SystemMonitor：プロセス・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常監視
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - AlertManager：LINE へプッシュ通知
  - streamlit ダッシュボード
- ポートフォリオ構築（portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 特徴量探索（将来リターン、IC、統計サマリー）
- AI（ai）
  - ニュース NLP による銘柄別センチメント生成（OpenAI 利用）
  - 市場レジーム判定（ETF + マクロニュースを合成）
- ツール
  - Paper Trading 向け検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 動作環境（推奨）
- Python 3.9+（typing / pathlib 等を利用）
- 必要パッケージ（一例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- 仮想環境（venv / pipenv / poetry 等）の利用を推奨

例（venv + pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # requirements.txt がない場合は上のパッケージ群を個別に pip install
```

---

## 環境変数 / .env
アプリは環境変数または .env / .env.local から設定を読み込みます（自動ロード。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI機能を使う場合必須）
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合は発注は MockBroker を使い、DB は paper_sqlite_path（data/paper_trading.db）へ分離
- PAPER_FILL_MODE — paper_trading の成交モード: `instant` | `partial` | `never` | `reject`（デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）  
  ※ Monitoring は環境にかかわらず本番 sqlite_path を使用（run_monitoring の設計）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知に使用

サンプル .env（抜粋）
```
KABUSYS_ENV=paper_trading
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境を作成してアクティブ化
3. 依存パッケージをインストール（requirements.txt がある場合はそれを使用）
4. .env を作成して必要な環境変数を設定
5. 必要なデータディレクトリを作成（例: data/）
6. DuckDB / SQLite の初期テーブルは起動スクリプトが自動で作成します（init_monitoring_db を呼び出す）

---

## 実行方法（主なスクリプト）
- 監視ループ起動（SystemMonitor のポーリング）
```
python -m kabusys.run_monitoring
# 環境変数で間隔を上書き可能:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
挙動:
- プロセス優先度を "high" に設定（可能な環境のみ）
- sqlite（monitoring）と DuckDB に接続して SystemMonitor を定期実行
- MONITOR_POLL_INTERVAL は 1 以上の整数でなければデフォルト 60 にフォールバック

- 実行エンジン（ExecutionEngine）起動
```
python -m kabusys.run_execution
# Paper trading モード:
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
挙動:
- プロセス優先度を "high" に設定（可能な環境のみ）
- KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し DB を data/paper_trading.db に分離
- Reconciler を実行し、ExecutionEngine を起動して取引セッションを実行

- streamlit ダッシュボード（監視）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
注意: ダッシュボードは監視用 SQLite を読み取り専用で開きます。MonitoringEngine を先に起動してください。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する例
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

---

## 注意点 / 運用上のメモ
- Monitoring は監視用 SQLite（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用します（意図的）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を用いることで本番 DB と完全に分離されます。
- プロセス優先度設定（psutil）や CPU affinity は実行ユーザーの権限によって失敗する場合があります。失敗時はログに警告され、処理は継続します。
- kill.flag（KILL_FLAG_PATH）を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch）。ExecutionEngine 側でこのフラグの検出・処理を行う設計になっています。
- OpenAI を用いる AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API エラー時はフェイルセーフによりスコアを 0 にする等のフォールバックが組み込まれています。
- .env の自動ロードはプロジェクトルートが特定できる場合に実行されます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要モジュール概要（短く）
- kabusys.config — 環境変数読み込み / Settings
- kabusys.execution — 発注ロジック、OrderManager、Reconciler、BrokerFactory など
- kabusys.monitoring — 各種監視、DB 永続化、アラート、streamlit ダッシュボード
- kabusys.portfolio — 候補選定、配分、リスク調整、ポジションサイズ計算
- kabusys.research — ファクター計算・特徴量探索・IC 計算
- kabusys.ai — news_nlp / regime_detector（OpenAI を用いたスコアリング）
- kabusys.utils — process_priority などユーティリティ

---

## ディレクトリ構成
（プロジェクト配下の主要ファイル／フォルダ一覧）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - (その他 execution 関連ファイル...)
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (ランタイムで作成されることを想定)
      - kabusys.duckdb (デフォルトパス)
      - monitoring.db (デフォルトパス)
      - paper_trading.db (paper_trading 時)
      - execution.pid
      - kill.flag

---

以上がこのコードベースの README（日本語）になります。必要であれば実行例や .env のテンプレート、依存関係の詳細（requirements.txt の内容）を追記できます。どの項目を詳しく示すか指示してください。