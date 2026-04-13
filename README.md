# KabuSys

KabuSys は日本株の自動売買システム向けユーティリティ群（Execution / Monitoring / Research / AI / Portfolio）です。本リポジトリは各コンポーネントの純粋関数や運用用ランタイム（起動スクリプト、監視、ストリームリットダッシュボード等）を含みます。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（起動例）およびディレクトリ構成を日本語でまとめています。

注意: 本 README は src/kabusys 配下の実装に基づき作成しています。実行には Python 3.10 以上を推奨します（型ヒントに union 型 "A | B" を使用）。

---

## プロジェクト概要

- 目的: 日本株自動売買システム（KabuSys）のコンポーネント群を提供し、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、ファクター計算／リサーチ（Research）、ニュース NLP／レジーム判定（AI）などをサポートする。
- 設計方針:
  - 各機能は可能な限り純粋関数／副作用の少ない実装を心がけ、DB 書き込みや外部 API 呼び出しは明示的に行う。
  - Paper Trading 環境では本番 DB と分離して動作する（data/paper_trading.db を使用）。
  - ルックアヘッドバイアス回避のため、日付参照や API 呼び出しの扱いに注意した実装。

---

## 機能一覧

主要な機能（抜粋）:

- Execution
  - OrderManager / ExecutionEngine / Reconciler：発注・状態管理・再起動時のリコンシリエーション
  - BrokerClientFactory によるブローカークライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - RiskManager（発注制限、利用率管理、サーキットブレーカーなど）

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringDB：SQLite ベースの監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch：フラグファイル (data/kill.flag) による ExecutionEngine 停止シグナル
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用 UI）

- Portfolio
  - 候補選定（select_candidates）、重み計算（等金額・スコア加重）
  - セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
  - 株数決定・単元丸め・集約キャップ処理（calc_position_sizes）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）を使ったニュースの銘柄別センチメントスコアリング（ai_scores へ書込）
  - regime_detector: ETF の MA200 乖離とマクロニュースセンチメントを合成して日次市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading データから検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順

1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. プロジェクトルートに .env を配置（任意）
   - 自動 .env ロードについて:
     - 実行時に .env / .env.local を自動読み込みします（OS 環境変数より優先度は低い）。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...        （必須: J-Quants API 用）
     - KABU_API_PASSWORD=...            （必須: kabuステーション API）
     - OPENAI_API_KEY=...               （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject  （Paper Trading の約定挙動）
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60         （監視ポーリング間隔秒）
     - LOG_LEVEL=INFO
   - .env の書式: export KEY=val や コメント行（#）に対応して読み込みます。

4. データディレクトリ作成
   - data フォルダを作成して DB 等を配置:
     - mkdir -p data

---

## 使い方（起動例・コマンド）

基本的にパッケージモードで起動できます（プロジェクトルートで実行）。

- ExecutionEngine を起動（本番／paper_trading 切替は KABUSYS_ENV）
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading は settings.is_paper=True になり、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と完全分離されます。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックします。
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に関係なく）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db が使われます）

- AI / リサーチ系（ライブラリ API）
  - ニューススコアリング: kabusys.ai.score_news（関数呼び出しで使用）
    - 例（Python 内から）:
      - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。失敗時はフォールバック動作を行う実装が多く、必須ではない場面もありますが、AI 機能はキーが無いと動作制約があります。

その他の注意点:
- 起動時にプロセス優先度を "high" に設定する処理が走ります（utils.process_priority.set_process_priority）。権限不足などで設定できない場合は警告ログになります。
- ExecutionEngine の停止制御は kill.flag（Settings.kill_flag_path）で行われます。KillSwitch は risk_monitor の結果等からフラグを書きます。
- MonitoringEngine は AlertManager 経由で LINE に通知できます（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が必要）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV (development | paper_trading | live) — 実行環境。デフォルト: development
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（Paper Trading の約定挙動、デフォルト: instant）
- PID_FILE_PATH — Execution PID ファイルのパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env 読み込みを無効化

---

## ディレクトリ構成（抜粋）

（src/kabusys 配下の主要ファイル / モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理（.env 自動ロード等）
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
    - utils/
      - __init__.py
      - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 監視テーブル初期化 / 永続化
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他: broker_factory, execution_engine, order_repository, etc.)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - (そのほか) data, strategy パッケージが連携している（prices_daily 等のテーブルを想定）

各ファイルの docstring と関数名が機能と設計方針を表しているため、コードのコメントも参照してください。

---

## 運用上のポイント / 注意事項

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に対して冪等にテーブルを作成し、必要に応じてカラム追加（簡易マイグレーション）を行います。
- Paper Trading の分離:
  - Paper Trading（KABUSYS_ENV=paper_trading）では paper_sqlite_path を使用して監視テーブル等を別 DB に保存します（本番 DB と完全分離）。
- AI 呼び出しについて:
  - OpenAI API 呼び出しはリトライ・バックオフ処理を含み、429 / タイムアウト / 5xx を想定しています。API レスポンスのバリデーションも実施します。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼びます。権限不足で設定できない場合はログに警告が出ますが、処理自体は継続します。
- kill.flag:
  - KillSwitch が書き込んだ kill.flag を使って ExecutionEngine に停止を通知します。Execution 側はこのフラグを確認して安全停止する必要があります。
- テスト/開発:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えばテスト時に自動 .env ロードを抑制できます。

---

必要があれば README をプロジェクトの実際の要件（セットアップの細部、requirements.txt、起動ユニットファイル、Dockerfile、CI 設定等）に合わせて拡張します。追加でドキュメント化したい箇所（API 仕様、DB スキーマ、デプロイ手順など）があれば教えてください。