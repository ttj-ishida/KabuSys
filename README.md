# KabuSys

日本株自動売買プラットフォームのコアライブラリ群と起動スクリプト群のリポジトリ。戦略のポートフォリオ構築、ポジションサイジング、発注管理、監視、研究用ファクター計算、OpenAI を使ったニュース NLP 等を含みます。

---

## プロジェクト概要

このコードベースは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine）: ブローカークライアント経由で注文を作成・管理し、リスク管理やリコンシリエーションを行う。
- 監視サブシステム（MonitoringEngine）: システム稼働状況、注文滞留・約定異常、ドローダウン等をポーリングしてログ・アラート・キルスイッチを管理する。
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム調整等の純粋関数群。
- 研究用モジュール（Research）: DuckDB 上の株価データを使ったファクター計算、将来リターン、IC 等の統計分析。
- AI モジュール（AI）: OpenAI を用いたニュースセンチメント（銘柄別）評価およびマクロセンチメントを合成した市場レジーム判定。
- ユーティリティ群: 設定管理、プロセス優先度設定、Streamlit ダッシュボード、各種ツール（例: Paper Trading 検証レポート生成）。

---

## 機能一覧

- Execution
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い、DB を分離
- Monitoring
  - SystemMonitor: CPU/MEM/Disk、Execution プロセス存在確認、データ鮮度検査
  - TradeMonitor: 滞留注文（stale）・約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ出力
  - KillSwitch: 条件で `data/kill.flag` を書き込むことで ExecutionEngine 停止シグナルを作成
  - AlertManager: LINE によるプッシュ通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定、スコア/等重み配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - モメンタム/ボラティリティ/バリューのファクター計算
  - 将来リターン、IC 計算、ファクター統計サマリ
- AI
  - 銘柄ニュースのセンチメント化（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB の検証レポート生成

---

## セットアップ手順

前提:
- Python 3.9+（パッケージの互換性に応じて調整）
- Git などでリポジトリをチェックアウト

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. data ディレクトリの準備
   - project_root/data を作成。実行時に自動作成される箇所もありますが、パーミッション等に注意してください。
   ```
   mkdir -p data
   ```

4. 環境変数設定
   - プロジェクトルートの `.env` または `.env.local` に設定するか、OS 環境変数として設定します。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意; デフォルト http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (AI 機能使用時に必要)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信時に必要)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒; デフォルト 60）
   - 注意: Settings クラスは自動で `.env` / `.env.local` をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化）。

5. DB 初期化
   - 監視用 SQLite テーブル (monitoring_db.init_monitoring_db) は run_monitoring / run_execution の起動時に自動で作成されます。
   - DuckDB は prices_daily / raw_financials 等のテーブルを必要に応じて用意してください（データ取得パイプラインは別実装）。

---

## 使い方

各スクリプトはパッケージモジュールとして実行できます。

1. ExecutionEngine を起動する
   - 通常起動（本番モード / Paper Trading の区別は KABUSYS_ENV）
   ```
   python -m kabusys.run_execution
   ```
   - 動作:
     - Settings を読み、SQLite/ DuckDB に接続
     - KABUSYS_ENV=paper_trading の場合は paper SQL を使い MockBrokerClient を使用（DB 分離）
     - エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag (stop フラグ) を監視して終了

2. Monitoring を起動する
   - 監視ループを開始:
   ```
   python -m kabusys.run_monitoring
   ```
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更（例: export MONITOR_POLL_INTERVAL=30）
   - 動作:
     - SystemMonitor, TradeMonitor, RiskMonitor を用いたチェックを定期実行し、SQLite にログを残す
     - 監視は環境に関わらず本番 sqlite_path を使用（監視データの一元化）

3. Streamlit ダッシュボード
   - 監視 DB を読み取り専用で可視化するダッシュボード:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - 起動時に DB が開けない場合はエラーが表示されます（MonitoringEngine を先に起動してください）。

4. Paper Trading 検証レポート生成
   - Paper Trading DB を解析してレポートを標準出力へ出すツール:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
   ```
   - 引数省略時は PAPER_TRADING_SQLITE_PATH 環境変数、さらに未設定なら data/paper_trading.db を参照。

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数か関数引数で指定）。
   - プログラム内 API を呼ぶ例（Python コードから直接呼ぶ）:
     - kabusys.ai.score_news(conn, target_date, api_key=...)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - 失敗や API エラー時はフェイルセーフ（部分的に 0 やスキップ）する設計。

6. 停止 / キルフラグ
   - 実行停止フラグ: project_root/data/stop_requested.flag が run_* スクリプトで監視されています。ファイルを作成するとポーリングループやエンジン起動ループが検知して停止します。
   - Kill Switch（監視が発動させる）: data/kill.flag — ExecutionEngine は起動時にこれが存在すると起動を行いません。KillSwitch.clear() を呼ぶか手動で削除してください。
   - PID ファイル: data/execution.pid 等に PID が書かれます。SystemMonitor は stale PID を検出して削除することがあります。

---

## 主な設定項目（抜粋）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、Execution は MockBroker を使用し DB は PAPER_TRADING_SQLITE_PATH に分離される
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（正の整数、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH: データベースファイルパス
- OPENAI_API_KEY: OpenAI を使う機能で必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の通知に使用

---

## ディレクトリ構成

以下は src/kabusys 下の主要ファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理（.env 自動ロード）
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring の起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - broker_api.py, broker_factory.py, ...（ブローカー抽象、実装）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - order_record.py
  - monitoring/
    - monitoring_db.py  — SQLite によるログ保存層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に使用/生成される)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid / kill.flag / stop_requested.flag

（注）上記は実装ファイルの抜粋です。実際のリポジトリには補助モジュールや追加実装が存在します。

---

## 運用上の注意点

- 監視（Monitoring）は本番 sqlite_path を使う設計のため、環境により誤って上書きしないよう .env を適切に設定してください。
- Paper Trading は本番 DB と分離されるよう実装されていますが、環境設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI API 呼び出しはレートリミットやネットワークエラーを想定してリトライ処理が組まれていますが、API キーの管理・コストに注意してください。
- Process priority / CPU affinity の設定はプラットフォーム依存のため十分な権限が必要です。設定できない場合は警告が出て処理は続行します。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news など）はデータパイプラインで事前に準備しておく必要があります（本リポジトリ内にデータ収集パイプラインは含まれていない場合があります）。

---

## 参考コマンドまとめ

- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれていない詳細な実装や拡張点については、各モジュールの docstring を参照してください。ドキュメントや運用手順の補足が必要であれば、目的別（デプロイ手順・環境変数テンプレート・DB スキーマ）に追加ドキュメントを作成します。