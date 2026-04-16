# KabuSys

日本株向けの自動売買 / 研究 / 監視フレームワーク（サンプル実装）

このリポジトリは、取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース NLU 等のコンポーネントを含む小規模な自動売買システムのコードベースです。テスト・検証用途に配慮した設計（Paper Trading 用 DB の分離、フェイルセーフ等）が組み込まれています。

---

## 主な特徴

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリによる実運用 / Paper Trading 分離
  - リコンシリエーション（起動時の注文・ポジション突合）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - Streamlit ベースの監視ダッシュボード
  - LINE によるプッシュ通知（AlertManager）
  - Kill Switch（特定条件で data/kill.flag を作成して ExecutionEngine を停止）

- Portfolio construction
  - 候補選定、重み計算（等金額・スコア重み）
  - セクター集中制限、レジーム乗数の適用
  - 発注株数決定（リスクベース、等分配、スコア重み）と単元丸め、aggregate cap

- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ

- AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp）
  - マクロニュースと ETF MA 乖離の合成による市場レジーム判定（ai.regime_detector）

- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 要求環境 / 依存パッケージ（代表例）

- Python 3.10+
- pip install で入れる主なパッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （※ 必要に応じてその他の実装依存パッケージが追加されることがあります）

例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

（プロジェクト配布に requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順（概要）

1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは個別インストール（上記参照）
4. 環境変数を設定（.env / .env.local をプロジェクトルートに置くことで自動読み込み）
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DB ファイルの初期化は各スクリプトが自動で行います（monitoring DB のテーブル作成等）

---

## 必要な環境変数（主なもの）

Settings クラスが参照する主要な環境変数とデフォルト値（存在しない場合は例を示します）:

- 必須（未設定時は例外を投げる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: INFO 等（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag をクリア
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視の閾値）
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager を使う場合）

例 (.env):
```
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxx
LINE_USER_ID=Uyyyyyyyy
```

注意:
- .env ファイルはプロジェクトルートに置くと自動ロードされます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 実行時は KABUSYS_ENV=paper_trading と設定すると、MockBrokerClient が使用され、専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番データベースとは分離されます。

---

## 使い方（代表的な実行例）

リポジトリルート（src を含む）で実行することを想定しています。

- 監視ループを起動（Monitoring）
  - 簡単な実行:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが検知して終了します（または Ctrl-C）。

- ExecutionEngine を起動（発注エンジン）
  - 本番（KABUSYS_ENV=live）または開発モード:
    - python -m kabusys.run_execution
  - Paper Trading（MockBroker を使用、DB 分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag の作成で実行スレッドに停止命令を送れます。ExecutionEngine は起動時に data/kill.flag を検査します（既に立っていると起動しません）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

- AI モジュール利用（例: ニューススコアリング）
  - Python スクリプト内で:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - OpenAI API key を環境変数 OPENAI_API_KEY に設定しておけば api_key を省略できます。

---

## 主要ファイル・ディレクトリ構成

（リポジトリ中の主要モジュール一覧。完全なツリーではありませんが主要ポイントを抜粋しています）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - run_monitoring.py               — SystemMonitor ポーリングループ起動
  - run_execution.py                — ExecutionEngine 起動
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py            — 市場レジーム算出（LLM + ETF MA）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite の永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等 — 一部は別ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - monitoring/                       (DB schema / monitors already noted)

- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - stop_requested.flag
  - kill.flag

（実際のファイル配置はリポジトリのルート構成に依存します）

---

## 運用上の注意 / 実装上の留意点

- Process Priority / CPU Affinity
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。権限がない場合は警告が出ますが処理は継続します。

- DB の扱い
  - monitoring 用 SQLite は init_monitoring_db() によりテーブル作成・簡易マイグレーションが行われます。
  - Paper Trading（KABUSYS_ENV=paper_trading）では paper_sqlite_path を使用し、本番 DB と分離されます。

- Kill / Stop フラグ
  - data/kill.flag: KillSwitch による ExecutionEngine 停止指示（監視が検知してファイルを書きます）。
  - data/stop_requested.flag: run_monitoring/run_execution がループ中に検知して安全停止します。
  - PID ファイル（data/execution.pid）は ExecutionEngine が使用し、不正な内容や stale PID を SystemMonitor が検出すると削除してアラートを記録します。

- AI（OpenAI）利用
  - OPENAI_API_KEY が必須（関数呼び出し時に api_key を渡すことも可）
  - LLM 呼び出しはリトライ・バックオフを実装しており、API 失敗時はフェイルセーフ（ゼロ等）で継続する設計です

- .env のパース
  - config._load_env_file はシンプルな .env パーサーを実装しています。コメント・クォート・export 形式に対応します。
  - OS 環境変数は保護され、.env.local の上書きでも OS 環境変数は上書きされません。

---

## 開発・デバッグのヒント

- 単体機能を手元で試す際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を用い、明示的に環境をセットして実行すると .env による影響を避けられます。
- Streamlit ダッシュボードは監視 DB を read-only URI で開くため、MonitoringEngine を先に起動してデータを作成してから閲覧してください。
- ロギングは各モジュールで logging.getLogger を使用しているため、デバッグ時はルートロガーのレベルを DEBUG に上げると詳細に追えます。

---

## 最後に

この README はコードベースの主要点を抜粋した概要ドキュメントです。実際の運用や拡張時は該当モジュール（monitoring/*.py, execution/*.py, ai/*.py, portfolio/*.py, research/*.py）内 docstring やコメントを参照してください。質問や追加で README に含めたい項目があれば教えてください。