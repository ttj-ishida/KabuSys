# KabuSys

日本株向けの自動売買システム（ライブラリ兼起動スクリプト群）。  
本リポジトリは以下の主要機能を含みます：戦略のためのファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・アラート（Monitoring）、およびニュースに基づく AI スコアリングなど。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下を想定したモジュール群で構成されています。

- データ解析 / 研究（DuckDB を使用したファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制約等）
- 発注レイヤ（ExecutionEngine、OrderManager、RiskManager、BrokerClientFactory）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch、アラート）
- AI モジュール（OpenAI を使ったニュース NLP・市場レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証ツール）
- ツール（ペーパートレード検証レポート生成など）

設計上のポイント：
- 本番・ペーパートレードを分離（KABUSYS_ENV による切替）
- DuckDB を分析用途に、SQLite を監視・履歴保存に使用
- 環境依存は .env（または環境変数）で設定可能。`config_setup` ウィザードで対話的に作成可
- AI 呼び出しは外部 OpenAI API を使用（API キーは環境変数または引数で与える）

---

## 主な機能一覧

- Execution（発注実行）
  - BrokerClientFactory により本番/モックを切り替え（KABUSYS_ENV=paper_trading でモック）
  - RiskManager によるポジション・ドローダウン等の制約
  - ExecutionEngine によるセッション実行 / PID 管理 / 停止フラグ対応

- Monitoring（監視）
  - SystemMonitor：CPU・メモリ・ディスク使用率、データ鮮度、Execution プロセス生存チェック
  - TradeMonitor：注文ログの監視（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：閾値超過時に `data/kill.flag` を書き込み、Execution を停止させる仕組み
  - MonitoringEngine：複数モニタの統合ポーリングとアラート送信

- Portfolio（ポートフォリオ構築）
  - 候補選定（スコア／ランクベース）
  - 等金額・スコア加重の重み計算
  - セクターキャップ適用
  - ポジションサイズ計算（リスクベース／等配分など）、単元株丸め・aggregate cap 対応

- Research（研究用）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB クエリ）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（OpenAI 統合）
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores テーブルへ格納
  - regime_detector: マクロ＋ETF MA200 を合成して日次の市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定でペーパートレード DB を解析）
  - 設定ウィザード（.env の対話式生成）
  - 設定検証 CLI（環境変数・config/*.yaml 等の検証）

---

## 必要な依存パッケージ（主要）

少なくとも次のパッケージが必要です（バージョンは環境に応じて調整してください）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（`validate_config` の YAML 内容検証用、任意だが推奨）
- （必要に応じて）sqlite3 は標準ライブラリに含まれます

pip 用の requirements.txt は本コードには含まれていません。開発環境であれば次のようにインストールします:

    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env の準備
   - 対話式ウィザードで作成:

         python -m kabusys.config_setup

   - もしくは手動でプロジェクトルートに `.env` を作成（例）:

         JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
         KABU_API_PASSWORD=your_kabu_api_password
         KABU_API_BASE_URL=http://localhost:18080/kabusapi
         DUCKDB_PATH=data/kabusys.duckdb
         SQLITE_PATH=data/monitoring.db
         KABUSYS_ENV=development
         LOG_LEVEL=INFO
         KILL_FLAG_CLEAR_ON_START=0
         # OPENAI_API_KEY=your_openai_api_key  # AI 機能を使う場合

   - .env は決してリポジトリにコミットしないでください。

4. 初期ディレクトリ作成（必要に応じて）:

       mkdir -p data logs

   - 起動スクリプトは起動時にログディレクトリ / data ディレクトリを自動作成することがありますが、権限などで失敗する場合があります。

5. 設定検証（任意）:

       python -m kabusys.validate_config
       # 警告も fail 扱いにしたい場合:
       python -m kabusys.validate_config --strict

---

## 使い方

### 起動スクリプト

- ExecutionEngine（発注エンジン）を起動

    python -m kabusys.run_execution

  振る舞い:
  - 環境変数 KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、ペーパートレード用の SQLite（`PAPER_TRADING_SQLITE_PATH` / default: `data/paper_trading.db`）へ記録します。本番環境とは分離されます。
  - `data/execution.pid` に PID を書き、`data/stop_requested.flag` の検出で停止します。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると kill flag を自動でクリアする挙動が有効になります（本番では推奨しません）。

- Monitoring（監視ループ）を起動

    python -m kabusys.run_monitoring

  振る舞い:
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を指定可能（デフォルト: 60）。
  - 監視用 DB（SQLite）と DuckDB を開いて監視処理を定期実行します。
  - `data/stop_requested.flag` の検出でループを終了します。

### 設定関連

- 対話式 .env 作成:

    python -m kabusys.config_setup

- 設定検証:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

### ペーパートレード検証レポート

ペーパートレード用 DB を解析して検証レポートを標準出力へ出力します:

    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

### ライブラリ（モジュール）利用例

- ファクター計算（研究）:

    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026, 4, 1))

- ニュース NLP（AI スコアリング）:

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数か api_key 引数で与える
    n_written = score_news(conn, date(2026, 04, 01), api_key="sk-xxxxx")

  注意点:
  - API キー未設定だと例外が発生します（ValueError）。
  - API 呼び出しは失敗時にリトライやフォールバックを行いますが、API の利用には料金が発生します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: モックブローカー・専用 SQLite 使用
  - live: 実取引（十分に注意して設定してください）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を利用する場合）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring で有効）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・停止関連）

---

## 停止・フラグ制御

- stop/terminate（手動で監視・実行ループを停止）
  - 停止要求はプロジェクトルート下の `data/stop_requested.flag` を作成することで run_* スクリプトが検知して終了します。
  - Kill Switch は `data/kill.flag` を作成して ExecutionEngine を停止させます（Monitoring が書き込む）。

- 実行中の PID ファイル:
  - `data/execution.pid` が ExecutionEngine により書き込まれます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / 設定取得ロジック
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py           — ニュースの LLM スコアリング
  - regime_detector.py    — 市場レジーム判定
- monitoring/
  - monitoring_db.py      — SQLite スキーマ・永続化層
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py      — （trade_monitor 実装が存在すると想定）
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py      — （アラート送信実装が存在すると想定）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルート（運用上のディレクトリ／ファイル）:
- data/                  — SQLite / pid / flag 等が置かれる（自動生成されることが多い）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                  — ログファイルはここに出力（デフォルト）

---

## 注意事項 / トラブルシューティング

- ログディレクトリの作成に失敗するとファイル出力が無効化され、コンソール出力のみになります（setup_logging が警告を出します）。
- process priority / CPU affinity の設定には権限が必要な場合があります。psutil によりアクセス拒否が発生すると警告が出てスキップされます。
- OpenAI を利用する機能は API キーと通信環境が必要で、API のレート制限や課金に注意してください。エラーハンドリングは組み込まれていますが、外部 API の可用性に依存します。
- 本番（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定等を必ず確認してください。`validate_config` の `--strict` モードで起動前にチェックすることを推奨します。

---

README はここまでです。さらに詳細なドキュメント（各モジュールの使用例・API 仕様・設定テンプレート）をご希望であれば、どのモジュール（例：ExecutionEngine、AI モジュール、ポートフォリオ作成フロー等）について深掘りするか教えてください。