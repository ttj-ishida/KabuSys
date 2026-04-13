# KabuSys

日本株自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、実行、監視、AI補助など）。  
このリポジトリはライブラリ兼軽量の実行スクリプト群を含み、ローカル/ペーパートレード/本番を想定した設定で動作します。

## 概要
KabuSys は以下の主要機能を持ちます。
- ファクター計算（Momentum / Volatility / Value 等）とリサーチユーティリティ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 実行エンジン用の注文管理・再整合（Reconciler / OrderManager 等）
- 監視基盤（System / Trade / Risk モニタリング、アラート、kill-switch）
- AI を利用したニュースセンチメント（OpenAI 経由）と市場レジーム判定
- ペーパートレード用の分離された DB と検証ツール（paper_verification_report）
- Streamlit ベースの監視ダッシュボード

設計方針の一部：
- DuckDB を使った時系列・財務データ処理（prices_daily / raw_financials 前提）
- SQLite を監視ログ・注文ログの永続化に使用
- OpenAI（gpt-4o-mini）をニュースセンチメントやレジーム判定に利用（失敗時は安全にフォールバック）
- 本番とペーパーは DB を分離して運用可能

---

## 機能一覧
主なコンポーネントと機能：
- kabusys.config.Settings: 環境変数・.env ロードと設定管理
- kabusys.utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- kabusys.research: ファクター計算（calc_momentum, calc_volatility, calc_value）・分析ユーティリティ（IC, forward returns 等）
- kabusys.portfolio: 候補選定・重み付け・セクター制限・ポジションサイズ計算
- kabusys.execution: BrokerFactory から BrokerClient を生成、OrderManager / Reconciler 等による発注・復旧処理
- kabusys.monitoring:
  - MonitoringDB: 監視用 SQLite スキーマ初期化・CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor: 定期チェックとログ記録
  - AlertManager: LINE Push による一方向通知（クールダウン管理）
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル書き込み
  - MonitoringEngine: 各モニタを束ねるポーリングループ
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- kabusys.ai:
  - news_nlp.score_news: raw_news → OpenAI による銘柄別センチメント書き込み（ai_scores テーブル）
  - regime_detector.score_regime: 1321 の MA とマクロ記事の LLM センチメントを合成して市場レジーム判定
- tools.paper_verification_report: ペーパートレードDBを元に運用検証レポートを生成

---

## 前提 / 必要パッケージ
（リポジトリに requirements.txt がない場合は目安として）
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit（Dashboard を使う場合）
- その他：標準ライブラリ（sqlite3 等）

仮想環境作成とパッケージインストールの例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. data ディレクトリを作成
```
mkdir -p data
```
4. 環境変数を設定（.env を利用可）。主要な環境変数（例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY (AI 機能を使うなら必須)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信時）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- MONITOR_POLL_INTERVAL（監視ループ間隔 秒、デフォルト 60）

例: .env
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

5. DB 初期化
- 監視テーブルは run_monitoring / run_execution が起動時に init_monitoring_db を呼びます。まずは run_monitoring を実行するか、Python から init_monitoring_db を呼んでください。

---

## 使い方

- 監視ループを起動（SystemMonitor 単体の起動スクリプト）
```
python -m kabusys.run_monitoring
```
- Execution Engine を起動（本番 / ペーパートレード判定は KABUSYS_ENV による）
```
python -m kabusys.run_execution
```
- ペーパートレード検証レポート（SQLite DB を指定して期間指定可能）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- Streamlit ダッシュボード（監視DB に対して read-only で表示）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- AI 機能
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または明示的に引数で渡す関数呼び出し）。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

注意点：
- run_execution は KABUSYS_ENV が `paper_trading` の場合、ペーパートレード用の MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離しています。
- run_monitoring は常に monitoring の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず production path を参照する意図あり）。
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。1 未満の値は無効扱いでデフォルトにフォールバックされます。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込むと ExecutionEngine 側で停止シグナルとして検出できます。KillSwitch はリスクアラート発生時にこのファイルを書きます。

---

## 主要スクリプト（起動ポイント）
- src/kabusys/run_monitoring.py
  - SystemMonitor を初期化しポーリングを実行。MONITOR_POLL_INTERVAL で間隔制御。プロセス優先度を high に設定。
- src/kabusys/run_execution.py
  - ExecutionEngine を組み立てて run_session() を開始。KABUSYS_ENV=paper_trading 時は paper DB を使用。
- src/kabusys/tools/paper_verification_report.py
  - ペーパートレード DB から運用指標（稼働率、注文成功率、送信率、レイテンシなど）を出力。

---

## ディレクトリ構成
（抜粋）

- src/
  - kabusys/
    - __init__.py  — パッケージ定義（バージョン等）
    - config.py  — Settings クラス・.env の自動読み込みロジック
    - utils/
      - process_priority.py  — プロセス優先度・CPU affinity ユーティリティ
    - ai/
      - news_nlp.py  — ニュースセンチメントの取得・OpenAI 呼び出し
      - regime_detector.py  — 市場レジーム判定
    - research/
      - factor_research.py  — Momentum / Volatility / Value 等のファクター計算
      - feature_exploration.py — 将来リターン、IC、統計サマリ
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - execution/
      - reconciler.py
      - order_manager.py
      - order_repository.py (参照あり)
      - execution_engine.py (参照あり)
      - broker_factory.py (参照あり)
      - order_record.py (参照)
    - monitoring/
      - monitoring_db.py  — SQLite スキーマ初期化と DB 操作ラッパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - tools/
      - paper_verification_report.py
    - data/ (実行時に作成、デフォルト DB 等を配置)
- README.md (本ファイル)

---

## 環境変数一覧（主なもの）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- LOG_LEVEL

---

## 運用上の注意
- DuckDB の prices_daily/raw_financials 等は別途データ投入パイプラインが必要です。本リポジトリはそれらテーブルを参照してファクター計算やレジーム判定を行います。
- OpenAI API 呼び出しを行う箇所はリトライとフォールバックを備えていますが、API キー・コスト・レート制限に注意してください。
- 実行プロセス優先度・CPU affinity を設定するためには権限が必要になる場合があります（psutil の例外はログに出力してスキップされます）。
- ペーパートレードは本番 DB と分離されています。ペーパートレードで実行する場合は KABUSYS_ENV=paper_trading を利用してください。

---

## 追加情報 / 開発者向け
- Settings はプロジェクトルートの .env / .env.local を自動でロードします（OS 環境変数 > .env.local > .env）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MonitoringDB.init_monitoring_db は冪等でマイグレーション（カラム追加）を行います。
- 各モジュールの関数は基本的に純粋関数または I/O を明示したインターフェース設計になっています。ユニットテストを容易にするため、外部 API 呼び出し部は差し替え可能（モック化）を意識した実装です。

---

必要であれば、セットアップ用の requirements.txt の例や、よく使うコマンドのスクリプト化（systemd ユニットや docker-compose のサンプル）も作成します。どの項目を優先して追加しますか？