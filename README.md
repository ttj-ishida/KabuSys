# KabuSys

日本株自動売買システムの一部モジュール群（Monitoring / Execution / Research / AI / Portfolio 等）。  
このリポジトリは、監視ループ・ExecutionEngine 起動スクリプト、Paper Trading 検証ツール、ファクター算出やニュース NLP、ポートフォリオ構築ロジックなどを含みます。

## プロジェクト概要
- 自動売買エンジン（実行・リコンシリエーション・リスク管理）
- 監視サブシステム（システム状態・注文滞留・リスクの継続監視、LINE 通知、Kill Switch）
- 研究モジュール（ファクター計算、特徴量探索）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- Paper Trading 向けの分離された DB と検証レポート生成

設計方針の例:
- DuckDB を価格・ファクターデータ用に使用、SQLite を監視ログ / 注文 DB に使用
- Paper Trading は本番 DB と分離（data/paper_trading.db 等）
- LLM（OpenAI）呼び出しはフェイルセーフにして部分失敗を許容
- 自動ロードされる .env（プロジェクトルートの .env / .env.local）をサポート

## 主な機能一覧
- Monitoring
  - system_monitor: CPU/メモリ/ディスク／プロセス／データ鮮度を監視しログ化
  - trade_monitor: 注文滞留・約定価格異常を検出しログ/リスクイベント記録
  - risk_monitor: ドローダウンやポジション上限を評価し kill.flag を書き込む
  - alert_manager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボードで監視状況を可視化
- Execution
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
  - Broker クライアントのファクトリ（paper_trading では Mock を使用）
  - リコンシリエーション（再起動時の注文照合・ポジション差分検出）
  - Order 管理（OrderManager / OrderRepository）
  - RiskManager（各種制限・サーキットブレーカー 等）
- Portfolio
  - 候補選定、等分配／スコア加重、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（momentum/value/volatility 等）
  - forward returns / IC 計算 / ファクターの統計サマリ
- AI
  - ニュース NLP による銘柄別センチメント（OpenAI）
  - 市場レジーム判定（ETF MA + マクロセンチメント）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作る:
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   ```
2. 必要パッケージをインストール（代表例）:
   ```
   pip install duckdb psutil requests streamlit openai
   ```
   （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数の設定:
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 主な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH: PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
     - LOG_LEVEL: DEBUG | INFO | ...（デフォルト: INFO）
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: それぞれ必須のケースあり（Settings._require により未設定で例外）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合に必要
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

   例 .env（最小）:
   ```
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

4. DB 初期化:
   - Monitoring 用 DB は run_monitoring / run_execution の起動処理内で init_monitoring_db() によって自動作成・マイグレーションされます。手動で作る必要は通常ありません。

## 使い方（主要スクリプト）
- 監視ループを起動（本番用監視プロセス）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 実行時にプロセス優先度を "high" に設定する処理が走ります（psutil 権限に依存）。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に関係なく monitoring は本番 DB を参照）。

- ExecutionEngine を起動（注文実行プロセス）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と完全分離）。
  - 実行前に必要な環境変数（KABU_API_PASSWORD など）を設定してください。

- Streamlit ダッシュボード（監視状況の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開き、Overview/Positions/Orders/System タブを提供します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB パスを指定できます。
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等の判定と PASS/FAIL を出力します。

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news (news_nlp.score_news) と kabusys.ai.regime_detector.score_regime を呼び出すためには OPENAI_API_KEY を設定してください。
  - OpenAI API 呼び出しはリトライやフェイルセーフ処理が組み込まれています。

## 主要ファイルとディレクトリ構成
（抜粋・説明付き）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings（自動 .env ロード、必須キーチェック、デフォルト値）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替含む）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と読み書き API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag による停止シグナル生成
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — 可視化用ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ...（注文管理・リコン処理）
    - broker_factory.py — Broker クライアント生成（本番 / モック切替）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・配分・リスク調整
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・解析
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（完全なツリーはリポジトリを参照してください）

## 注意点 / トラブルシューティング
- 環境変数の自動読み込み:
  - デフォルトでプロジェクトルート（.git または pyproject.toml）から .env / .env.local を読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等に DB スキーマを作成し、必要なカラムがなければ ALTER を行う軽量マイグレーションを含みます（例: trade_logs.latency_ms, dashboard.peak_value）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは run_execution が paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと完全分離します。
- OpenAI API:
  - AI 機能は OPENAI_API_KEY が必須。API のレート制限やネットワーク障害はリトライロジックで扱いますが、キーが未設定だと例外になります。
- LINE 通知:
  - LINE token や user_id が未設定だと通知はスキップされ、ログに記録されます。
- プロセス優先度:
  - set_process_priority は psutil の実装や権限に依存します。AccessDenied 等が発生した場合は警告ログを出してスキップします。

## 開発メモ / テスト関連
- 各モジュールは副作用を極力抑え、ユニットテストしやすい純粋関数群（portfolio / research）と I/O 層（monitoring_db / OrderRepository 等）に分離されています。
- OpenAI 呼び出し箇所は内部でラップしているため、unittest.mock.patch で差し替えてテスト可能です（news_nlp._call_openai_api, regime_detector._call_openai_api など）。

---

この README はコードベースから抽出した要点をまとめたものです。実運用時は .env.example を参照し、必要な API キーやパスを適切に設定してください。質問や追加ドキュメントが必要であれば教えてください。