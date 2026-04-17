# KabuSys

日本株自動売買システムのミニマル実装リポジトリ。ポートフォリオ構築、注文実行、監視、調査用ファクター計算、ニュースNLP（OpenAI）などの主要コンポーネントを含みます。本リポジトリはモジュール群を提供し、実行・監視のためのエントリポイントスクリプトおよびユーティリティも含まれます。

---

## 概要

KabuSys は以下の主要機能を持つ自動売買フレームワークです。

- 注文作成・管理・再同期（OrderManager, Reconciler）
- 実取引（kabuステーション等）とペーパー取引の切替（BrokerClientFactory）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（SystemMonitor）と監視エンジン（MonitoringEngine）
- 監視ログ永続化（SQLite）および分析用 DuckDB
- ニュースの NLP による銘柄センチメント評価（OpenAI 利用）
- 市場レジーム判定（レジームスコアの合成）
- ポートフォリオ候補選定・重み付け・株数算出の純関数群（portfolio モジュール）
- Streamlit ダッシュボード、検証レポート生成ツール等の補助ツール

設計思想の一部：
- DB は SQLite（監視・発注ログ等）と DuckDB（時系列・集計）を併用
- 環境変数 / .env による設定管理（Settings）
- Paper Trading モードは本番 DB と分離（data/paper_trading.db）
- 外部 API（OpenAI / LINE 等）呼び出しは失敗時にフェイルセーフ設計

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数/.env ロード、Settings クラス（KABUSYS_ENV, DB パス, 各種閾値 等）
- kabusys.execution
  - ExecutionEngine（run_execution 起動スクリプト）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringDB（SQLite スキーマ初期化・読み書き）
  - MonitoringEngine（複数モニタのポーリング）
  - streamlit_dashboard（監視データ可視化）
- kabusys.portfolio
  - 候補選定、重み付け、ポジションサイズ算出、セクター制約、レジーム乗数
- kabusys.research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
- kabusys.ai
  - news_nlp（ニュースを OpenAI でスコアリングして ai_scores に書込）
  - regime_detector（ETF MA とマクロニュースセンチメントの合成）
- kabusys.tools
  - paper_verification_report（Paper Trading 検証レポート生成）
- kabusys.utils
  - process_priority（プロセス優先度 / CPU affinity）

---

## 前提 / 必要要件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit （ダッシュボードを利用する場合）
- SQLite は標準ライブラリに含まれます。

推奨: 仮想環境（venv / poetry / pipenv 等）を利用してください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

※ requirements.txt はリポジトリに付属していない想定のため、上記パッケージを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存パッケージをインストール
3. data ディレクトリを作成（自動生成される箇所もありますが事前に作ると便利）
   ```bash
   mkdir -p data
   ```
4. 環境変数を設定（.env / .env.local を使用可能）
   - 最低限必要な環境変数（用途に応じて）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabu API ）
     - OPENAI_API_KEY（OpenAI を使う機能）
   - 任意 / 推奨:
     - KABUSYS_ENV = development | paper_trading | live
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
     - LOG_LEVEL（DEBUG|INFO|...）
   - .env 例:
     ```
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```

5. DB 初期化
   - 監視用 DB スキーマは run_monitoring / run_execution 実行時に自動で作成されます（init_monitoring_db）。

---

## 実行方法（使い方）

- 実行エンジン（ExecutionEngine）を起動
  - 本番/開発/ペーパーは KABUSYS_ENV で切替
  - ペーパートレードでは MockBrokerClient を使い、paper_trading DB に記録されます
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中に停止させる場合はプロジェクトの data/stop_requested.flag を作成するとスレッドが検知して停止します（スクリプト内で STOP_FLAG をチェック）。
  - 実行時は data/execution.pid に PID を書きます。

- 監視ポーリング（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を変更:
    ```bash
    export MONITOR_POLL_INTERVAL=30  # 30秒間隔
    ```
  - run_monitoring は monitoring DB（settings.sqlite_path）と DuckDB を開いて SystemMonitor のポーリングを行います。
  - 停止は data/stop_requested.flag を作成することで行います。

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開いてダッシュボード表示します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）

- AI 機能（ニュース NLP / レジーム判定）
  - プログラムから関数を呼び出して利用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - OpenAI API キーは OPENAI_API_KEY 環境変数か、関数引数で与えます。

---

## 設定（主な環境変数）

- KABUSYS_ENV — 実行モード（development / paper_trading / live）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパー時の約定モード（instant / partial / never / reject）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH — KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）

詳しくは kabusys.config.Settings のプロパティを参照してください。

---

## 停止・強制停止の仕組み

- stop_requested.flag
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しており、存在するとループを終了します（手動停止用）。
- kill.flag（KillSwitch）
  - RiskMonitor 等でしきい値を超えた場合に KillSwitch が KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込むと、ExecutionEngine 側で検知して停止処理を行います（自動安全停止）。
  - Settings.kill_flag_clear_on_start を使うと起動時に既存の kill.flag をクリアできます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / .env ロード・Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

モジュール別:
- ai/
  - news_nlp.py — ニュースの OpenAI スコアリング（ai_scores へ書込）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
- execution/
  - execution_engine.py (実行エンジン本体) — （参照あり）
  - order_manager.py — 注文操作の外向き API
  - order_repository.py — DB 永続化（SQLite）
  - reconciler.py — 起動時の自動リコンシリエーション
  - broker_factory.py / broker_api.py — ブローカー抽象化
  - risk_manager.py — 発注前リスク判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ & 永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE へのアラート送信
  - monitoring_engine.py — まとめてポーリング
  - streamlit_dashboard.py — 可視化（Streamlit）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py — IC / 将来リターン / 統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- data/ (ランタイムで使用する既定の場所)
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用)

---

## 開発・運用上の注意

- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI / LINE 等の外部サービス利用は API レートやエラーに応じたリトライ・フォールバックを実装していますが、API キー・課金設定に注意してください。
- プロセス優先度設定や CPU affinity は psutil を利用しています。権限がないと警告が出ますが動作は継続します。
- DuckDB のバージョン差分や executemany の制約（空リスト不可）に注意した実装になっています。
- ルックアヘッドバイアス回避のため、AI モジュールやレジーム判定は内部で現在時刻を直接参照しない設計になっています。日付は明示して渡してください。

---

## サポート / 貢献

- バグ報告や改善提案は Issue にてお願いします。
- 主要な変更はドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に従って行ってください（リポジトリ外にある場合があります）。

---

この README はコードベースを読み解いてまとめたものであり、実際の運用時には環境依存の設定（API キー、ブローカー接続情報、ファイルパス等）を必ず確認してください。必要であれば各モジュールのドキュメントやソースに基づく詳細な運用手順を別途作成できます。