# KabuSys

日本株自動売買システムの一部（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリングなど）の実装コードベース向け README。

以下はコードベース（src/kabusys/*）を基にした概要、機能、セットアップ・実行方法、ディレクトリ構成の説明です。開発者向けの参考ドキュメントとしてご利用ください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を提供するライブラリ／アプリケーション群です。主要な責務は次のとおりです。

- ExecutionEngine：ブローカー経由での注文生成・送信・状態管理・リコンシリエーション
- MonitoringEngine：プロセス・システム状態、注文やリスクの監視・アラート
- Portfolio Construction：候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research：ファクター計算、将来リターン計算、IC（情報係数）など
- AI コンポーネント：ニュース記事からのセンチメントスコアリング、レジーム判定（OpenAI API）
- ユーティリティ：設定管理、プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成など

設計方針として、外部 API 呼び出しや永続化の扱いを分離し、テストしやすい純粋関数群と副作用を伴う層（DB / ブローカー / API）を明確に分けています。

---

## 主な機能一覧

- 実行（Execution）
  - OrderManager、OrderRepository、Reconciler による注文管理・再整合
  - Paper trading モード（環境変数 `KABUSYS_ENV=paper_trading`）では MockBroker を使用し、専用 DB に分離
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク、プロセス生存、株価データ鮮度の監視
  - TradeMonitor：滞留注文（stale）、約定価格の異常（price anomaly）監視
  - RiskMonitor：ドローダウン・ポジション上限のチェックとリスクログ記録
  - KillSwitch：特定条件でフラグファイルにより ExecutionEngine を停止させる仕組み
  - AlertManager：LINE Messaging API 経由の通知（クールダウン制御あり）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア重み、リスクベースのポジションサイズ算出
  - セクター集中制限、レジームに応じた乗数（資金調整）
- リサーチ
  - Momentum / Volatility / Value ファクター算出（DuckDB 経由で prices_daily, raw_financials を参照）
  - 将来リターン、IC、基本統計量
- AI
  - ニュース記事をまとめて OpenAI（gpt-4o-mini）へ送り銘柄別のセンチメントを ai_scores に書き込む
  - レジーム判定（ETF ma200 とマクロニュースセンチメントを合成）
- ツール
  - paper_verification_report：Paper Trading 用検証レポート生成（稼働率、注文成功率、P95 レイテンシ等）
- 設定管理
  - `kabusys.config.Settings` による環境変数 / .env ロード、妥当性チェック

---

## 前提（Prerequisites）

- Python 3.9+（コードは typing/新しい構文を利用）
- 必要な主要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク（OpenAI API、LINE API を利用する場合）

パッケージはプロジェクトに requirements.txt が無い場合、手動でインストールしてください。例：

pip install duckdb psutil requests openai streamlit

（プロジェクトでは他のライブラリやバージョン制約がある可能性があるため、実運用時は適切に固定してください）

---

## セットアップ手順

1. リポジトリをチェックアウトし、Python 環境（仮想環境）を用意する
2. 必要なパッケージをインストール（上記参照）
3. 環境変数を設定する
   - 簡単にはプロジェクトルートに `.env` を作成（.env.example を参考に）
   - 自動ロード機能:
     - デフォルトでプロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を読み込みます
     - 読み込み順序: OS 環境変数 > .env.local > .env
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. 主要な環境変数（主なもの）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - paper_trading の場合は ExecutionEngine が MockBroker を使用し、paper DB に書き込む
   - OPENAI_API_KEY: OpenAI API を利用する機能で必要
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（使用箇所がある場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
   - DUCKDB_PATH（default: data/kabusys.duckdb）
   - SQLITE_PATH（default: data/monitoring.db） — Monitoring 用（run_monitoring は環境にかかわらず本番 sqlite_path を使用する）
   - PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db） — paper_trading 用 DB
   - PAPER_FILL_MODE（instant | partial | never | reject）（paper trading の挙動）
   - PID_FILE_PATH（default: data/execution.pid）
   - KILL_FLAG_PATH（default: data/kill.flag）
   - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等
5. データディレクトリを作る
   - デフォルトでは `data/` 以下に DB / pid / flag を作成します。必要に応じてディレクトリを作成してください。

---

## 使い方（主要コマンド / スクリプト）

コード中に起動スクリプトが用意されています。ソースを直接参照する場合は `PYTHONPATH=src` を指定するか、パッケージとしてインストールしてください。例は開発ディレクトリから実行する方法です。

- Monitoring（監視ループ起動）
  - 説明: SystemMonitor のポーリングループを開始し、monitoring DB にログを書き込みます。監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）。
  - ポーリング間隔: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）
  - 実行例:
    - PYTHONPATH=src python -m kabusys.run_monitoring
  - 重要: 実行開始時にプロセス優先度を "high" に設定する試みを行います（プラットフォームに依存）。

- Execution（実行エンジン）
  - 説明: ExecutionEngine を起動して取引セッションを実行。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper DB（data/paper_trading.db）に書き込みます。
  - 実行例:
    - PYTHONPATH=src python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定し、Reconciler による起動時同期（リコン）などを実行します。

- Streamlit ダッシュボード（監視 UI）
  - 説明: Monitoring DB（読み取り専用）を表示する簡易ダッシュボード。
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - 説明: Paper Trading DB のログを集計して検証レポートを出力します。
  - 実行例:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report
    - 指定期間:
      - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パス指定:
      - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（ニューススコア／レジーム判定）
  - 実装はモジュール関数として提供されています（OpenAI API キー必須）。
  - 例:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 注意: これらは外部 API（OpenAI）を呼び出すため、API キーの設定とレート制御・エラーハンドリングに注意してください。

---

## 重要な挙動・運用注意

- Monitoring は環境にかかわらず production sqlite_path を使用する（run_monitoring のドキュメントに明示）。
- Execution の paper_trading モードは DB を完全に分離（paper_sqlite_path）しており、本番データと混ざらない設計。
- .env の自動ロードはプロジェクトルート探索により行われるため、実行するカレントディレクトリではなくソース配置に依存します。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- kill.flag（デフォルト data/kill.flag）は KillSwitch により書き込まれ、ExecutionEngine 側で読み取ることで安全に停止させるための仕組みです。Execution 起動時にフラグをクリアするオプション（Settings.kill_flag_clear_on_start）があります。
- DB マイグレーション（軽微なスキーマ追加）は `init_monitoring_db` が冪等で実施します（起動時にテーブル・インデックスを作成し、必要なカラムがなければ ALTER で追加）。

---

## 開発向けディレクトリ構成（主要ファイル抜粋）

プロジェクトは src/kabusys 以下に各モジュールを配置しています。主要なファイル構成は以下の通り（抜粋）：

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / .env の読み込み・Settings
    - run_monitoring.py                 — Monitoring ポーリングループ起動スクリプト
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py    — Paper Trading 検証レポート生成スクリプト
    - monitoring/
      - __init__.py
      - monitoring_db.py                — SQLite を使った永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
      - order_repository.py (参照あり)
      - order_record.py (参照あり)
      - broker_factory.py (参照あり)
      - execution_engine.py (参照あり)
      - ...（その他 Execution 関連）
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
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (想定)
      - kabusys.duckdb (DuckDB データファイル)
      - monitoring.db (SQLite 監視ログ)
      - paper_trading.db (Paper Trading 用 SQLite)

（実際のリポジトリではさらに多くのファイル・モジュールが存在します。上は主な入口と機能ごとの分割を示したものです）

---

## 設定項目（主な環境変数一覧）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが妥当性チェックあり）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須として参照箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定モード）
- PID_FILE_PATH: PID ファイルパス（default data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイルパス（default data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: "1" にすると ExecutionEngine 起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視用閾値

詳細は `kabusys.config.Settings` を参照してください。Settings クラスは値の妥当性チェックやデフォルトを提供します。

---

## テスト・デバッグのヒント

- DuckDB / SQLite の接続はコード内で生成されるため、読み取り専用 URI（sqlite://?mode=ro のような）を使って Streamlit から DB を読むと安全です（streamlit_dashboard では URI 組み立て済み）。
- OpenAI API 呼び出しはリトライ / バックオフ実装が施されていますが、テストでは API 呼び出し部分をモックするのが簡単です（score_news._call_openai_api / regime_detector._call_openai_api は patch 可能）。
- process priority や CPU affinity の設定はプラットフォーム依存で失敗することがあるため、Warning ログに注目してください。
- MonitoringDB の init は冪等なので起動スクリプトを複数回実行しても安全です。

---

この README はコードベースから主要な使い方と挙動を抜粋してまとめたものです。詳細な実装／API の仕様は各モジュールの docstring とソースをご確認ください。追加で README に載せたい内容（例: 実行例の詳細、CI 手順、依存パッケージの固定、.env.example のテンプレート等）があれば指示してください。