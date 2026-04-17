# KabuSys

日本株の自動売買・リサーチ基盤（モジュール群）  
このリポジトリは、取引実行、監視、ポートフォリオ構築、ファクター計算、AI（ニュースNLP / レジーム判定）などを含む自動売買システムのコアロジックを集めたコードベースです。

対応 Python バージョン: 3.10+（型注釈に | 演算子を使用しています）

---

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution: ブローカーへの発注、注文管理、再同期（Reconciler）などの実行ロジック
- Monitoring: システム稼働監視、注文監視、リスク監視、LINE アラート、監視ダッシュボード（Streamlit）
- Portfolio: 銘柄選定、重み算出、ポジションサイズ計算、セクター制限などのポートフォリオ構築ロジック
- Research: DuckDB を使ったファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- AI: OpenAI を用いたニュースセンチメントスコアリング（news_nlp）、市場レジーム判定（regime_detector）
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプト
- Config: .env 自動読み込み・環境設定管理（Settings クラス）

設計方針の一部:
- DuckDB / SQLite を使ってオンプレミスでデータを処理・永続化
- 本番・Paper Trading の DB は分離（環境変数で切替）
- OpenAI を使う機能は API キーが必須で、失敗時はフェイルセーフに振る舞う

---

## 主な機能一覧

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化 / MockBroker（paper_trading 用）
  - OrderManager、OrderRepository、Reconciler（自動復旧）

- 監視系
  - SystemMonitor：CPU/メモリ/ディスク、実行プロセス PID、データ鮮度のチェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション数の検出とイベント記録
  - KillSwitch：条件に応じて停止フラグ（data/kill.flag）を書き込み実行系を停止
  - AlertManager：LINE へのプッシュ通知（クールダウン管理）
  - MonitoringEngine：上記モニタを纏めてポーリング
  - Streamlit ダッシュボード（読み取り専用で監視 DB を表示）

- ポートフォリオ関連
  - 銘柄選定（select_candidates）
  - 等重・スコア加重の重み算出
  - ポジションサイズ決定（リスクベース / 等配分）および aggregate cap の調整
  - セクター制限・レジーム乗数の適用

- リサーチ（DuckDB ベース）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（OpenAI）
  - ニュース記事を銘柄ごとに集約して LLM でセンチメント評価 → ai_scores に格納
  - マクロニュースと ETF（1321）の MA200 を合成して市場レジームを判定し market_regime に書き込み

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な外部依存:
     - duckdb, psutil, openai, requests, streamlit

   例（明示的にインストールする場合）:
   - pip install duckdb psutil openai requests streamlit

4. パッケージを開発モードでインストール（任意、モジュールを python -m kabusys... で使いやすくする）
   - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須 (代表例):
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - Optional / 推奨:
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   KABUSYS_ENV=paper_trading
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

---

## 使い方（主なコマンド）

前提: パッケージをインストール済み、またはプロジェクトルートから PYTHONPATH を通して実行可能であること。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録する（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在する場合、エンジンは起動せず終了します。
    - 停止は data/stop_requested.flag を作るか、kill.flag によるシグナルにより行われます。

- 監視ループ（SystemMonitor のポーリング）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）（デフォルト 60）
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
    - 停止: data/stop_requested.flag を作成するとループが終了します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を表示します（DB がなければ起動エラーになります）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で別の SQLite ファイルを指定可能（デフォルト: data/paper_trading.db）

- AI 機能
  - ニューススコアリング（プログラム内で呼ぶ API）
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

- モジュール単体テスト的利用
  - MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor 等はインスタンスを生成して run_once() / check_once() を呼べます（ユニットテスト向け）。

---

## 停止／フラグファイル

- 終了要求フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag — 存在するとループが検知して終了する
- Kill Switch による強制停止（ExecutionEngine 停止シグナル）
  - data/kill.flag — KillSwitch が書き込むと ExecutionEngine 停止を示す
  - KillSwitch はリスク条件（ドローダウン超過・ポジション上限超過等）で書き込まれる

ExecutionEngine 起動時に kill_flag_clear_on_start 設定が有効であれば起動時に kill.flag を自動削除するオプションが Settings に用意されています。

---

## 主要なディレクトリ構成（src/kabusys）

- __init__.py
- config.py
  - Settings クラス (.env 自動読み込み、必須 env の検証)
- run_execution.py
  - ExecutionEngine を組み立てて起動する CLI スクリプト
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- ai/
  - news_nlp.py        — ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.py — マクロ + ETF MA を使った市場レジーム判定

- monitoring/
  - monitoring_db.py   — SQLite 用の永続層（init / CRUD）
  - system_monitor.py  — CPU・メモリ・ディスク・データ鮮度・PID の監視
  - trade_monitor.py   — 注文滞留、約定異常価格の検出
  - risk_monitor.py    — ドローダウン・ポジション数監視
  - alert_manager.py   — LINE Push 通知
  - kill_switch.py     — kill.flag の書き込み
  - monitoring_engine.py — モニタ群をまとめる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード

- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py
  - broker_factory.py, broker_api.py など（ブローカー関連インターフェース）
  - order_record.py（注文状態モデル）
  （実際のブローカー実装 or Mock はここに配置）

- portfolio/
  - portfolio_builder.py  — 銘柄選定 / スコアソート
  - position_sizing.py    — 発注株数決定ロジック
  - risk_adjustment.py    — セクター制限・レジーム乗数

- research/
  - factor_research.py    — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- data/
  - （実行時に使用されるデータディレクトリ。デフォルト DB ファイル等）

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

---

## 設定（Settings）についての補足

- .env/.env.local はプロジェクトルートに置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能利用時必須)
  - KABUSYS_ENV (development | paper_trading | live)
  - PAPER_FILL_MODE (paper_trading の注文約定挙動: instant|partial|never|reject)
  - SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

Settings クラスは厳密に値のバリデーションを行うため、無効な値を指定すると起動時に ValueError を投げます。

---

## 運用上の注意・設計メモ

- Monitoring は環境に関わらず本番の sqlite_path を参照します（監視は本番データに対して行うため）。
- Paper Trading は実行/DB を本番から分離する設計（settings.is_paper により paper_sqlite_path を使用）。
- OpenAI を使う処理は外部 API に依存するため、API キー・レート制限・エラーに対する堅牢なリトライ／フェイルセーフ処理を実装していますが、運用では API 利用量やコストに注意してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で参照します。起動時に DB がないとエラーとなるため、MonitoringEngine 起動後に閲覧する運用を想定しています。

---

この README はコードベースの公開 API・起動手順の概要です。内部実装（ExecutionEngine の詳細な設定、Broker 実装、Strategy モデル等）は各モジュールの docstring やソースコメントを参照してください。質問や追加ドキュメント（例: デプロイ手順、コンテナ化、CI）をご希望の場合は教えてください。