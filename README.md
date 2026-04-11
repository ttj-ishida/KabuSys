# KabuSys

軽量な日本株自動売買 / リサーチ基盤のモジュール群です。シグナルに基づく発注エンジン、監視/アラート、ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（起動コマンド例）およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムと研究用ユーティリティの集合です。主な目的は次のとおりです。

- シグナルを受けてブローカーへ発注する ExecutionEngine（発注の堅牢性・リコンシリエーションを考慮）
- 実行・監視のための Monitoring サブシステム（システム状態／注文状況／リスク監視・アラート・kill switch）
- ポートフォリオ構築（候補選定、重み付け、単元調整、リスク調整）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリューなど）および特徴量解析
- AI（OpenAI）を使ったニュースセンチメント評価 / レジーム判定
- Streamlit ベースの監視ダッシュボード

設計方針として、DB（DuckDB / SQLite）やブローカーアクセスは明示的に切り分けられ、フェイルセーフ（API失敗時のフォールバック）やクラッシュ後の復旧（Reconciler）が考慮されています。

---

## 主な機能一覧

- Execution
  - Signal Queue ベースの発注フロー（OrderManager / ExecutionEngine）
  - Reconciler による起動時の注文照合とポジション差分検出
  - RiskManager による Gate 検査（シグナル・発注レート・回路遮断など）
  - paper_trading モード（モックブローカー、専用 SQLite DB へ記録）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス PID、データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限を監視、dashboard 更新
  - KillSwitch：閾値到達時にフラグファイルを書き ExecutionEngine に停止を促す
  - AlertManager：LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- Portfolio（純粋関数）
  - 候補選定（スコア降順）
  - 等重・スコア重み計算
  - 単元丸め・リスクベースのポジションサイズ算出
  - セクターキャップ・レジーム乗数算出

- Research
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）
  - ニュース集合を LLM でセンチメント化して ai_scores テーブルへ保存
  - マクロニュース＋ETF MA200 による市場レジーム判定

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がある場合はそちらを使用）。

   例（主要依存のみ）:

   ```
   pip install duckdb psutil openai requests streamlit
   ```

   開発時は logger やテスト用に追加パッケージが必要になる場合があります。

3. 環境変数設定

   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

   最低限設定が必要な変数（例）:

   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI機能を使う場合 必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development

   データベース/ファイルパスのデフォルト:

   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
   - PID_FILE_PATH: data/execution.pid
   - KILL_FLAG_PATH: data/kill.flag

   その他の設定（例）:

   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の模擬約定挙動）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）

   例 .env（用途に合わせて編集）:

   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   JQUANTS_REFRESH_TOKEN=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方・起動例

ファイルは Python パッケージとして配置されており、モジュールとして起動できます（パッケージルートが PYTHONPATH にある前提）。

- Monitoring の起動（ポーリング監視ループ）

  - デフォルト動作：MONITOR_POLL_INTERVAL 環境変数でループ間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（監視 DB は本番 DB を直接参照する想定）。

  コマンド例:

  ```
  # パッケージとして実行
  python -m kabusys.run_monitoring

  # 直接スクリプト実行（環境によりパス調整）
  python src/kabusys/run_monitoring.py

  # ポーリング間隔を変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  起動時にプロセスの優先度を "high" に設定します（set_process_priority 呼び出し）。OS によっては権限不足で失敗する場合があります（警告でスキップされます）。

- ExecutionEngine の起動（発注エンジン）

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（paper trading 用）を使用し、DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます。
  - 通常は本番 DB（settings.sqlite_path）を使用します。

  コマンド例:

  ```
  # 本番 / 開発モード
  python -m kabusys.run_execution

  # Paper trading モード（専用 DB に記録）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  ExecutionEngine は起動時に pid ファイルを扱い、kill.flag により外部から停止シグナルを受けられます。Settings.kill_flag_clear_on_start を使って起動時にフラグを自動でクリアする設定もあります。

- Streamlit ダッシュボード

  監視データを可視化する簡易 UI があります。

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  ストリームリット起動時、データベースは読み取り専用 URI で開かれます（モニタリング実行中の DB を安全に参照）。

- AI 機能（ニュース NLP / レジーム判定）

  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続を受け取り、raw_news / prices_daily 等のテーブルを参照して結果を DB に書き込みます。API 呼び出し失敗時はフェイルセーフでスコアをスキップまたは中立値にフォールバックします。

---

## 重要な挙動・注意点

- Settings の自動ロード
  - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- monitoring は常に production sqlite_path を使う（KABUSYS_ENV に依存しない）
  - run_monitoring は環境変数にかかわらず settings.sqlite_path を用いて監視テーブルを初期化・記録します。

- Paper trading の完全分離
  - KABUSYS_ENV=paper_trading 時はブローカークライアントは MockBrokerClient を返し、DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録されます。本番 DB と分離されます。

- Kill switch / PID
  - ExecutionEngine 側は pid_file（data/execution.pid）を用いてプロセス存在を監視。KillSwitch はファイル data/kill.flag を作成して外部から停止を要求します（冪等性あり）。

- ポリシーとフォールバック
  - AI 呼び出しでの一時エラー（429・ネットワーク障害・5xx）には指数バックオフでリトライ。パース失敗等は警告ログを出してフェイルセーフにフォールバックします。
  - DuckDB に対する executemany の空リスト制約に配慮した実装（空リストの場合は書き込みをスキップ）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル/モジュールの一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings
    - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - utils/
      - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite 監視ログ層（init / MonitoringDB）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py            — 注文永続化（SQLite）
      - order_record.py                — 注文状態遷移等のドメインロジック
      - reconciler.py
      - broker_api.py                  — ブローカー API 抽象（および実装ファクトリ）
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py

この README に記載のない補助的なモジュール（data パイプライン、ブローカ実装、OrderRepository 詳細など）も同ソースツリー内に存在します。コード中の docstring に詳細設計や注意点が書かれているため、実装変更時は docstring を参照してください。

---

## 開発・テストのヒント

- MonitoringEngine.run_once は単発実行（テスト用）に便利です。ユニットテストから個別 monitor をモックして呼び出せます。
- AI 関連の外部呼び出しは内部の `_call_openai_api` を patch/mock してテスト可能です（README 内の docstring にも注記あり）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）を事前にロードしておくと research / ai 機能をローカルで試せます。

---

必要に応じて、この README をベースにインストール要件（requirements.txt）、運用ガイド（systemd ユニット例、コンテナ化手順）や .env.example を追加できます。補足や特定部分の詳細化（例: ExecutionEngine の具体的なシグナルフォーマット、Broker 実装の説明）をご希望であればお知らせください。