# KabuSys

日本株向けの自動売買システム（プロトタイプ）。戦略のポートフォリオ構築、発注実行、監視・アラート、研究用ファクター計算、ニュース NLP を用いたセンチメント評価などの機能を含むモジュール群で構成されています。

主な目的は「実運用に近い形でのエンジン設計および運用オペレーションの検証」です。コードはモジュール化されており、paper_trading（モックブローカー）で実動作を検証しつつ、live 環境へ移行できる設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 重要な環境変数・設定

---

## プロジェクト概要

KabuSys は以下の主要領域をカバーします。

- Execution：発注・注文管理・リコンシリエーション（再起動後の同期）などの実行ロジック
- Monitoring：プロセス稼働監視・データ鮮度・注文滞留・リスク（ドローダウン／ポジション数）監視、LINE 通知、kill flag による安全停止
- Portfolio：銘柄選定、重み付け、サイズ算出、セクター制限・レジーム乗数などのポートフォリオ構築ユーティリティ（純粋関数）
- Research：DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）・IC 計算など
- AI：ニュース NLP（OpenAI）による銘柄別センチメント評価、マクロニュースとETF の MA を合わせた市場レジーム判定
- Tools：Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード 等

設計上のポイント：
- 設定は環境変数および .env/.env.local（自動読み込み）が優先される
- paper_trading と live は DB を分離して運用できる
- DuckDB を分析用データベース、SQLite を監視／注文ログ等の永続層に使用

---

## 機能一覧

主要機能の抜粋：

- 実行周り
  - OrderManager：注文の状態遷移管理（create/send/sync/cancel）
  - Reconciler：起動時のブローカー照合とポジション差分検出
  - BrokerFactory：環境に応じたブローカークライアント生成（paper_trading ではモック）

- 監視周り
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ記録
  - KillSwitch：条件到達時に flag ファイルを書いて ExecutionEngine を停止させる
  - AlertManager：LINE Messaging API を用いたプッシュ通知
  - Streamlit ダッシュボード：監視情報の可視化（read-only 接続）

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等金額／スコア重み付け
  - 単元株丸め、リスク中心のポジションサイズ算出
  - セクター上限適用、レジーム乗数

- リサーチ／AI
  - DuckDB を使った factor 計算（momentum/value/volatility）
  - 将来リターン・IC（Spearman）計算
  - ニュースを LLM（OpenAI）でスコア化して ai_scores に書き込み
  - マクロセンチメント + ETF MA200 乖離で日次レジーム判定

- ツール
  - paper_verification_report：Paper Trading 用検証レポートを生成
  - Monitor 起動スクリプト / Execution 起動スクリプト

---

## セットアップ手順

前提
- Python 3.10+（ソース中での型注釈（|）等を使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ: duckdb, psutil, openai, requests, streamlit

例（venv を使う場合）:
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt があればそれを使用）
   - pip install duckdb psutil openai requests streamlit
   - （追加で実行ユーティリティやテスト用パッケージがあれば適宜追加）
4. データディレクトリ作成（デフォルト）
   - mkdir -p data

自動的に .env / .env.local がプロジェクトルートにあれば起動時に読み込まれます（ただし OS 環境変数が優先）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期 DB の準備
- Monitoring 起動スクリプトや Execution 起動スクリプトは起動時に SQLite のスキーマ初期化（init_monitoring_db）を行います。手動でスキーマを作成する必要は通常ありません。

---

## 使い方（実行例）

環境変数の最低限の例（本番であれば適切に設定してください）:
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI を使う機能が必要な場合
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 実ブローカーやデータ取得に必要（本番のみ）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB を分ける場合に指定

起動スクリプト
- 監視ループを起動（MONITOR_POLL_INTERVAL でポーリング秒数を上書き可能; デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 環境変数例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（KABUSYS_ENV=paper_trading のときはモックブローカーを使用し paper_trading 用 DB に記録）
  - python -m kabusys.run_execution
  - 例（paper_trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

Streamlit ダッシュボード（監視 DB を read-only で参照）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション: --db PATH で DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH に優先）

AI / リサーチ機能（コード経由）
- kabusys.ai.score_news(conn, target_date, api_key) — raw_news を読み ai_scores に書き込む
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key) — market_regime を書き込む
- research の関数は DuckDB 接続と日付を与えて呼び出す（例: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic）

注意事項
- run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようとします。権限によっては失敗して警告が出ますが起動自体は継続されます。
- Paper Trading 環境は本番の SQLite DB と分離されるため検証に安全です（設定によりパスを変更可能）。

---

## 主要ディレクトリ構成

（src/kabusys 以下の概観）

- kabusys/
  - __init__.py
  - config.py                   — 環境変数/.env ロードと Settings クラス
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト（paper_trading でモック利用）
  - ai/
    - news_nlp.py               — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py        — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/                        — （※データ関連モジュールは別ファイルにある想定）
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                       — ブローカーとのやり取り、OrderRepository 等
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ初期化 + MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py        — psutil を使った優先度 / affinity の設定ユーティリティ

補足：
- DuckDB を分析用 DB（デフォルト path: data/kabusys.duckdb）
- Monitoring 用 SQLite（デフォルト path: data/monitoring.db）
- Paper trading 用 SQLite（デフォルト path: data/paper_trading.db）

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の	fill 動作（instant|partial|never|reject; default: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の必須トークン（設定必須の場合あり）

config.py 内の Settings クラスでさらに細かいプロパティ（閾値や各種パス）を参照できます。未設定の必須変数にアクセスすると例外が発生します。

---

## 運用上の注意

- paper_trading モードは本番 DB と完全に分離して動作するよう設計されています。検証時は必ず KABUSYS_ENV=paper_trading を確認してください。
- OpenAI を用いる機能（news_nlp, regime_detector）は API コストとレイテンシの要件があります。API キーとレート制限に注意してください（内部でリトライとバックオフを実装）。
- kill.flag による停止は冪等（既に存在すれば再書込しない）です。ExecutionEngine は起動時に設定に応じて kill.flag をクリアできます。
- monitoring の各種閾値（CPU/MEM/DISK 等）は Settings から調整可能です。

---

もし README に追加したい具体的な説明（たとえば ExecutionEngine のシーケンス図、Order state machine の遷移表、または DB スキーマの詳細など）があれば教えてください。必要に応じて追記・拡張します。