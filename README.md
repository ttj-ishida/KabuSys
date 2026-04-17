# KabuSys

KabuSys は日本株自動売買システムのコンポーネント群です。本リポジトリには、発注エンジン、監視・アラート、ポートフォリオ構築ユーティリティ、リサーチ/ファクター計算、AI を利用したニュース評価など、トレーディングシステムに必要な主要機能が含まれます。

以下はこのコードベースの概要、主要機能、セットアップと実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 言語: Python
- 構成:
  - ExecutionEngine: ブローカー連携による発注・注文管理、リスク管理、再起動時のリコンシリエーション
  - Monitoring: システム状態・注文の監視、アラート（LINE）、kill スイッチ（フラグファイルによるエンジン停止）
  - Portfolio: 候補選定、配分・株数決定、セクター制約・レジーム乗数
  - Research: DuckDB を用いたファクター計算・特徴量探索（prices_daily / raw_financials を参照）
  - AI: OpenAI を用いたニュースセンチメント評価（ai/news_nlp）および市場レジーム判定（ai/regime_detector）
  - Tools: Paper Trading 用の検証レポート生成などのユーティリティ
  - Utilities: プロセス優先度設定、設定読み込み等

設計方針の例:
- DuckDB をローカル分析用に使用し、研究系コードは価格・財務テーブルのみ参照（実取引 API にアクセスしない）。
- 環境や日付管理はルックアヘッドバイアスに注意して実装（target_date を受け取る等）。
- フェイルセーフ: API/外部エラー時は例外を吸収して継続する箇所が多い。

---

## 機能一覧（ハイライト）

- 発注・注文管理
  - OrderManager、OrderRepository、ExecutionEngine、Reconciler による注文ライフサイクル管理と再同期
- リスク管理
  - RiskManager（設定による取引制限）、RiskMonitor（ドローダウン・ポジション上限監視）
- 監視・アラート
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - MonitoringEngine: 定期ポーリング、KillSwitch（閾値で停止フラグ書き込み）
  - AlertManager: LINE push による通知（クールダウン付き）
  - Streamlit ダッシュボード（read-only）による監視可視化
- ポートフォリオ構築
  - 候補選定（スコア順）、等重/スコア重み、リスクベース／等分配の株数算定、セクター上限適用、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュースを銘柄ごとにセンチメント評価 → ai_scores に書込
  - regime_detector: ETF (1321) の MA とマクロニュースでレジームを判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成
- 設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）と Settings クラス

---

## 必須・推奨環境

- Python 3.9+（typing の一部構文に依存）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード実行時）
- OS: Linux / macOS / Windows（process priority はプラットフォーム差分あり）

※ requirements.txt は本リポジトリに含まれていないため、プロジェクトで使うパッケージを適宜 pip install してください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くことが可能（自動ロード）。
   - 自動ロード無効化が必要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須の利用箇所のみ）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能利用時）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH: ファイルパスの上書き

5. データディレクトリ
   - data/ 以下に DB やフラグファイル（execution.pid, kill.flag, stop_requested.flag など）を配置。
   - 監視ループやエンジンはこれらのファイルを参照・作成します。

---

## 使い方（代表的な起動方法）

※ 実行はプロジェクトルートから行うことを推奨します（.env 自動読み込みのため）。

1. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 挙動:
     - PROCESS 優先度を high に設定（可能な場合）
     - Settings から sqlite_path を取得して監視 DB に接続（監視は常に sqlite_path を使用）
     - DuckDB 接続も作成
     - SystemMonitor.check_once を定期実行（MONITOR_POLL_INTERVAL 秒、デフォルト 60）
   - 停止:
     - data/stop_requested.flag を作成するとループは終了します（スクリプトは検出して終了）。

2. ExecutionEngine 起動（発注エンジン）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path に記録（本番 DB と分離）
     - ブローカークライアント生成 → OrderRepository, OrderManager, RiskManager, Reconciler 組立
     - Engine.run_session を別スレッドで起動し、stop フラグ（data/stop_requested.flag）をポーリングして停止
     - 起動時に stop フラグが既にあれば起動せず終了する
   - 注意:
     - 実稼働時は KABUSYS_ENV=live を指定するなど環境に応じた設定を行ってください

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db data/paper_trading.db （または環境変数 PAPER_TRADING_SQLITE_PATH）

4. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を read-only モードで開き可視化（起動中の MonitoringEngine がデータを書き込む前提）

5. AI 機能
   - OpenAI API を利用する機能（news_nlp.score_news / regime_detector.score_regime）を呼ぶ際は OPENAI_API_KEY を設定してください。
   - API のリトライや失敗時のフォールバック（例: macro_sentiment=0.0）を実装済み。

---

## フラグ / PID / 停止の仕組み

- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視しており、ファイルがあると処理を安全に終了します（管理者が強制的に停止したい場合に使用）。
- kill.flag
  - KillSwitch は閾値（ドローダウンやポジション上限）に達した場合 data/kill.flag を書き込むことで ExecutionEngine を停止させる「ソフトキル」信号を作ります。
  - KillSwitch.clear() で削除可能（Execution 起動時に消去オプションあり）。
- PID ファイル
  - ExecutionEngine は data/execution.pid に PID を書くことで SystemMonitor などがプロセス有無を検出します。
  - stale な PID（実際のプロセスが存在しない）を SystemMonitor が検出すると PID ファイルを削除し、リスクイベントとして記録します。

---

## 設定（Settings と .env の挙動）

- Settings クラスが環境変数を参照して各種パスや動作を決定します。
- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を特定し、.env を読み込み（override=False）、.env.local を上書き（override=True）します。ただし OS 環境変数は保護されます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 重要な設定項目（例）
  - KABUSYS_ENV: development | paper_trading | live
  - OPENAI_API_KEY: OpenAI 利用時に必要
  - PAPER_FILL_MODE: paper_trading の約定モード
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH

---

## トラブルシューティング（よくある注意点）

- psutil によるプロセス優先度設定:
  - 権限が不足すると AccessDenied になり優先度設定がスキップされる旨の警告が出ます（正常）。
- OpenAI API:
  - リクエスト時に 429 / ネットワークエラー / タイムアウト / 5xx は指数バックオフでリトライ。最大リトライ回数到達時はフェイルセーフのデフォルト値で継続。
- DuckDB / SQLite のファイルロック:
  - Streamlit などから読み取り専用で開く場合は URI モードで read-only を指定している点に注意（ストリームリットの起動例を参照）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成と簡単なマイグレーション（カラム追加）を行います。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールを含む src/kabusys 以下の概観です（実際のファイル数は多め）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/                          — （実行時）data ディレクトリ（DB・フラグ）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル定義・ラッパー（MonitoringDB）
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
    - (その他 broker_factory, execution_engine, order_repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py

（上記は主要ファイルの抜粋です。実際には execution 以下にブローカー関連や order_repository 等の詳細実装が含まれます。）

---

## 開発メモ / 注意点

- 研究（research）・AI（ai）モジュールは外部 API・本番 API を直接呼ばないよう設計されている部分がありますが、AI 部分は OpenAI へリクエストするためキーと通信環境が必要です。
- paper_trading 環境は本番データと完全分離されるように、明示的に paper_sqlite_path を使用するようになっています。テスト運用時は KABUSYS_ENV=paper_trading を利用してください。
- ログレベルは Settings.log_level で制御できます（環境変数 LOG_LEVEL）。
- コード内に多くのフェイルセーフ（例外吸収・ログ出力）があるため、エラーがあってもプロセスは継続するケースが多い点を理解しておいてください（運用時はログ監視が重要です）。

---

以上が README の要点です。必要であれば、サンプル .env.example、requirements.txt、起動スクリプト（systemd / supervisord）向けのユニットファイルテンプレートなども用意できます。どの追加情報が必要か教えてください。