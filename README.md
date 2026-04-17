# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の主要コンポーネント群を含みます。バックエンドのポートフォリオ構築、注文管理、モニタリング、AI（ニュース NLP / レジーム判定）、および検証ツールが実装されています。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール式の自動売買フレームワークです。

- 戦略側で算出したシグナルに基づくポートフォリオ構築（候補選定 / 重み付け / ポジションサイズ算出）
- 注文管理とブローカー API 抽象化（ExecutionEngine / OrderManager）
- 起動時のリコンシリエーション（Reconciler）
- 実行系（ExecutionEngine）と監視系（MonitoringEngine）の分離
- 監視ログの永続化（SQLite）とダッシュボード（Streamlit）
- Paper Trading モード（本番 DB と分離、Mock ブローカー）
- ニュースを LLM（OpenAI）で評価する AI モジュール（ニュース NLP、レジーム判定）
- 検証ツール（Paper Trading の検証レポート等）

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定（score / rank ベース）
  - 等金額／スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（リスクベース、単元株丸め、利用可能現金に合わせたスケーリング）
- 注文管理・実行
  - OrderManager / OrderRepository による状態管理
  - BrokerClientFactory による本番／モックブローカー切替（KABUSYS_ENV）
  - Reconciler による再起動後の自動復旧
- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働/データ鮮度
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager（LINE への通知）
  - MonitoringEngine による定期ポーリング
  - Streamlit ベースのダッシュボード
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングし ai_scores に格納
  - マクロ記事 + ETF MA200 乖離を合成して市場レジーム判定
  - 再試行・エラーハンドリング、レスポンス検証を備えた安全設計
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing の | 記法などを使用）
- SQLite は標準ライブラリ、別途 DuckDB・psutil・requests・openai・streamlit 等が必要

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール（requirements.txt がない場合は下記をインストール）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   ※ 実際のプロジェクトでは requirements.txt を作成して管理してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 必須例（.env に記載する例）:
     ```
     KABUSYS_ENV=development         # development | paper_trading | live
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
   - 重要な設定:
     - KABUSYS_ENV: 実行モード（paper_trading のときは paper_trading 用 DB を使用）
     - OPENAI_API_KEY: AI 機能を使う場合に必須
     - PAPER_FILL_MODE: paper_trading の模擬約定挙動（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視ログ DB（デフォルト: data/monitoring.db）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. データディレクトリの作成
   ```bash
   mkdir -p data
   ```

---

## 使い方

以下は主要な起動方法と使用例です。

- 実行エンジン（ExecutionEngine）を起動
  - 目的: 注文の実行・注文管理を行うプロセスを起動
  - コマンド:
    ```bash
    python -m kabusys.run_execution
    ```
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。
    - 起動時に data/kill.flag があるとエンジンは起動をスキップします。KillSwitch を使って停止指示を出す設計です。
    - 実行中は data/execution.pid に PID が書かれます。

- 監視ループ（MonitoringEngine ベース）を起動
  - 目的: SystemMonitor/TradeMonitor/RiskMonitor を定期実行して監視ログを蓄積
  - コマンド:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - オプション（環境変数）:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存せず本番 DB を参照する設計）。

- Streamlit ダッシュボード（監視データ閲覧）
  - コマンド:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - データベースは read-only で開くため、MonitoringEngine が稼働してデータがあることを確認してください。

- Paper Trading 検証レポート生成
  - コマンド:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB: data/paper_trading.db。`--db PATH` で別ファイルを指定できます。

- AI 機能をスクリプト／モジュールから呼ぶ
  - ニューススコア付与:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - 注意: API キーは引数または環境変数 OPENAI_API_KEY で与える必要があります。失敗時のフォールバックやリトライが組み込まれていますが、キー未設定では例外になります。

- その他ユーティリティ
  - kill.flag の確認 / クリア:
    - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を使います。ExecutionEngine 起動時に消去するオプション（KILL_FLAG_CLEAR_ON_START）もあります。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証トークン（必須箇所あり）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）設定
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読む処理を無効化できます（テスト等で便利）。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — Settings クラス（環境変数読み込みと検証）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 発注株数算出
    - risk_adjustment.py — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 / 永続化層（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 管理
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（注文処理、ブローカー抽象化）
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し / バリデーション）
    - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロセンチメント）
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (リポジトリに含めることを想定)
    - monitoring.db （デフォルト監視 DB）
    - kabusys.duckdb （DuckDB）
    - paper_trading.db （Paper Trading 用 SQLite）
    - kill.flag / stop_requested.flag / execution.pid など制御用フラグファイル

---

## 運用上の注意

- KABUSYS_ENV を `live` にして実行する場合は、ブローカー API 資格情報や外部通知設定等を適切に管理してください。誤った設定で実行すると実取引につながる可能性があります。
- Paper Trading モードは production DB と分離される設計ですが、環境変数やパスの設定を確認してください。
- AI 機能（OpenAI）には API 利用料が発生する場合があります。キーの管理・レート制限に注意してください。
- Monitoring は本番 sqlite_path を参照するため、監視プロセスは本番 DB への書き込みを行います。テスト時は設定を切り替えるか専用 DB を使ってください。
- process priority / CPU affinity の設定は OS によって制限される場合があり、権限不足で失敗することがあります（警告ログが出ますが処理は継続します）。

---

## よくある操作例

- 監視ポーリング間隔を 30 秒に変更して起動:
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading 確認レポート（別 DB）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-03-01 --to 2026-03-31 --db /path/to/paper_trading.db
  ```

- Streamlit ダッシュボードで別監視 DB を指定:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db /path/to/monitoring.db
  ```

---

この README はコードベースの主要機能と運用方法をまとめたものです。より詳細な API や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）がある場合は併せて参照してください。必要があればセットアップの自動化 (docker / systemd unit / supervisor) や CI 用の手順例も追加できます。ご指示ください。