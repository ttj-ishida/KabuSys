# KabuSys

KabuSys は日本株向けの自動売買・調査・監視フレームワークです。  
ポートフォリオ構築、発注エンジン、監視・アラート、ファクター研究、ニュース NLP（LLM）によるセンチメント評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・停止・ツール）
- 環境変数 / .env の例
- ディレクトリ構成

---

プロジェクト概要
- 日本株の自動売買ワークフローを構成するライブラリ／実行スクリプト群。
- 主要コンポーネント:
  - 発注/実行エンジン（ExecutionEngine, OrderManager, BrokerClientFactory 等）
  - ポートフォリオ構築（候補選定・重み付け・リスク調整・株数算出）
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - アラート（LINE push 経由）
  - 研究・ファクター計算（DuckDB を用いた factor 計算）
  - AI モジュール（ニュース NLP / 市場レジーム判定） — OpenAI API を用いる
  - Paper Trading モード（本番 DB と分離して動作）

---

主な機能一覧
- Execution
  - 実際のブローカークライアントを差し替え可能。`paper_trading` 環境では MockBroker を利用して専用 DB に記録。
  - 起動時のリコンシリエーション機能で OrderSent 等の整合性回復。
  - RiskManager による発注制御（利用率・最大ポジション比率等）。

- Portfolio（銘柄選定・配分）
  - シグナルに基づく候補選定（スコア順）
  - 等金額・スコア加重・リスクベースなど複数の割当方式
  - セクター上限・レジームに応じた乗数適用

- Monitoring（監視）
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の最終 price 日付を参照）
  - 注文滞留・約定異常の検出
  - ドローダウン / ポジション上限監視
  - kill.flag（ExecutionEngine 停止）生成の自動判定（KillSwitch）
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

- Research（研究用途）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリ

- AI（OpenAI）
  - ニュース記事を LLM に渡して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書込み
  - マクロニュース + ETF(ma200) を組み合わせた市場レジーム判定（bull/neutral/bear）

- ユーティリティ
  - .env ロード（Settings）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - SQLite / DuckDB のパス設定、paper_trading 用 DB 分離
  - Paper Trading 用検証レポート生成ツール

---

動作要件（目安）
- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- SQLite（標準ライブラリで可）
- ネットワーク: OpenAI / LINE API 利用時は外部接続必須

requirements.txt がない場合は以下でインストールしてください（プロジェクトの venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env ファイルをプロジェクトルートに作成（下記サンプル参照）
5. data ディレクトリを作成（起動中に自動生成される場合もありますが、手動で作ると便利）
   ```bash
   mkdir -p data
   ```
6. DuckDB / SQLite DB の初期化は各モジュール起動時に必要テーブルを作成する仕組みになっています（init_monitoring_db 等）。

---

主要な実行・運用コマンド（例）

- ExecutionEngine 起動
  - 本番または開発:
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - Paper trading:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 実行はデーモン化 / systemd 等でラップすることを推奨。

- Monitoring 起動（プロセス監視ポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）。デフォルト 60 秒。
    ```bash
    MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  --db オプションで別 DB を指定できます。

- AI モジュール（ライブラリ関数として利用）
  - ニューススコア付け: kabusys.ai.score_news(conn, target_date, api_key)
  - レジームスコア付け: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

停止 / 強制終了
- 実行中ループ（run_execution / run_monitoring）はプロジェクトルートの data/stop_requested.flag を検知して自動停止します。停止したい場合はファイルを作成してください:
  ```bash
  touch data/stop_requested.flag
  ```
- ExecutionEngine に対して外部から停止シグナルを送りたい（KillSwitch）は data/kill.flag を書き込むか、監視側が自動で生成します。KillSwitch は Settings.kill_flag_path を参照します。

---

環境変数（主要）
- 基本（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API 用
- OpenAI
  - OPENAI_API_KEY — ニュース NLP / レジーム判定で必要
- KabuSys 動作制御
  - KABUSYS_ENV — development|paper_trading|live（デフォルト: development）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を指定すると .env 自動読み込みを無効化
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- Paper Trading 動作
  - PAPER_FILL_MODE — instant|partial|never|reject（デフォルト: instant）
- Monitoring / 実行
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 1 で起動時に kill.flag をクリア
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）

.env の例
```
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API keys
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=xxx
OPENAI_API_KEY=sk-...

# DB paths (相対パス可)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# LINE alert (任意)
LINE_CHANNEL_ACCESS_TOKEN=xxxxx
LINE_USER_ID=Uxxxxxxxxxxxxxxxxxx
```

---

停止フラグ / PID ファイルの説明
- data/execution.pid: ExecutionEngine が自身の PID を書き出すファイル。SystemMonitor はこのファイルの PID 存在を確認してプロセス生存チェックを行う。
- data/stop_requested.flag: run_monitoring / run_execution の各起動スクリプトはこのファイルの存在を検知するとループを抜けて安全にシャットダウンする。
- data/kill.flag: KillSwitch（監視）により書き込まれると、ExecutionEngine 側が安全停止のトリガーとして利用できる。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 発注株数計算
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化・読み書きラッパ
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 送信
    - monitoring_engine.py — 全体ポーリングの統合
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・再同期関連
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに execution の broker 関連や data モジュールなどが含まれる可能性があります）

---

運用上の注意
- Paper Trading は本番用 DB と完全に分離する設計です（PAPER_TRADING_SQLITE_PATH を参照）。
- OpenAI API や LINE API の呼び出しは外部サービスに依存するため、API キーの管理・レート制限への配慮が必要です。
- set_process_priority はプラットフォーム依存（Windows / POSIX）で動作を変えます。権限不足時は警告を出してスキップされます。
- DuckDB / SQLite のファイルロックや並列アクセスには注意してください（読み取り専用接続やコミットタイミングを考慮）。

---

貢献・拡張
- Broker クライアントの追加（BrokerClientFactory）
- 手数料・スリッページモデルの改善（position_sizing の cost_buffer 等）
- 銘柄別単元株数対応（lot_size の拡張）
- モニタリング指標・アラート基準のチューニング

---

問題や質問があれば README に追記します。README に含めたい追加情報（CI、テスト方法、詳細なデプロイ手順等）があれば教えてください。