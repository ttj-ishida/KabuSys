# KabuSys

KabuSys は日本株向けの自動売買（アルゴリズム取引）および監視フレームワークです。ポートフォリオ構成、注文実行、モニタリング、リスク管理、ニュース NLP（LLM）評価、研究用ファクター計算などのコンポーネントを備えています。本リポジトリは主要ロジックを純粋関数・モジュールに分離しており、ローカル開発・Paper Trading・本番運用（live）を想定した設計になっています。

この README はリポジトリ内の主要機能説明、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## 主な特徴（機能一覧）

- Execution（発注系）
  - ExecutionEngine / OrderManager / Reconciler による注文送信・状態管理、再起動後の自動リコンシリエーション
  - Broker クライアントを切り替え可能（paper_trading 時は MockBrokerClient を使用し DB を分離）
  - リスク管理（RiskManager）による発注前チェック（ポジション比率、資金利用率、サーキットブレーカー等）

- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文（stale order）・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - MonitoringEngine：複数モニタをまとめてポーリングしアラート発行・キルスイッチ評価
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視結果の可視化）

- Portfolio（銘柄選定・サイズ計算）
  - 候補選定、等金額・スコア加重配分、セクターキャップ、レジームに基づく乗数、株数計算（lot 単位丸め・aggregate cap）

- Research（研究用）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（LLM を用いた機能）
  - news_nlp: raw_news をまとめて OpenAI（gpt-4o-mini 等）に送信し銘柄別センチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200乖離 + マクロニュース LLM センチメントを合成して日次レジームを判定し market_regime テーブルへ書き込み
  - API 呼び出しは冪等性・リトライ・フェイルセーフ設計

- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを生成（稼働率・注文成功率・API レイテンシ等）

- 設定管理
  - Settings クラスおよび .env 自動ロード（.env/.env.local）をサポート。環境変数で挙動を制御

---

## セットアップ

必要な前提・依存関係（例）
- Python 3.10+
- 必要パッケージ（pip でインストール）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （その他、プロジェクトで利用しているパッケージがあれば追加）

例: 仮想環境作成・依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

環境変数（主なもの）
- 必須（実行に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY — OpenAI API キー
- 実行環境指定
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading: Execution は paper_trading 専用 DB を利用（data/paper_trading.db、設定で上書き可能）
- DB パス等（デフォルト値あり）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- その他
  - PAPER_FILL_MODE — paper_trading の注文約定モード（instant | partial | never | reject）デフォルト "instant"
  - PID_FILE_PATH / KILL_FLAG_PATH / PID ファイル・kill flag のパス
  - LOG_LEVEL — ログレベル

.env の自動ロード
- プロジェクトルート（.git または pyproject.toml が見つかった場所）から .env/.env.local を自動読み込みします。
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意: .env.example 等を参考に .env を用意してください。

---

## 使い方（代表的な実行例）

プロジェクトルートから実行する想定です（src をパッケージとして扱う）。

1) Execution Engine を起動
- Paper Trading（環境分離）で動かす例:
  - 環境変数: KABUSYS_ENV=paper_trading
  - コマンド:
    ```bash
    # モジュール実行が可能な場合
    python -m kabusys.run_execution
    # または直接スクリプトを実行
    python src/kabusys/run_execution.py
    ```
  - 実行時、paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。

2) Monitoring（監視ループ）を起動
- MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（デフォルト 60 秒）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  # または
  python src/kabusys/run_monitoring.py
  ```
- 監視プロセスは常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

3) Streamlit ダッシュボード（監視結果の可視化）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
--db オプションで監視 DB のパスを指定できます。

4) Paper Trading 検証レポートの生成
```bash
# 指定期間でレポートを生成
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または単に
python -m kabusys.tools.paper_verification_report
# --db オプションで DB パスを指定可能
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5) AI 機能（ニューススコア／レジーム判定）
- Python から関数を呼び出す形で利用します（例: score_news / score_regime）。OPENAI_API_KEY を設定してください。
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 4, 1), api_key="sk-...")
  ```
- 実際の運用ではスクリプト化して cron やバッチで呼ぶことを推奨します。

停止・キル機構
- run_execution / run_monitoring はプロジェクトの data ディレクトリにあるフラグファイルでの制御をサポートします:
  - data/stop_requested.flag — 存在すると監視/実行ループが終了します（run_execution はこのフラグを検知するとエンジンを停止）
  - data/kill.flag — KillSwitch で書き込まれるファイル。ExecutionEngine に対する停止シグナルとして利用します。
- PID ファイル: data/execution.pid（実行中のプロセス PID を書く想定）。SystemMonitor が stale PID を検出すると削除・アラートを出します。

ログ・プロセス優先度
- 起動時に process priority を "high" に設定する呼び出しが行われます（プラットフォーム依存で権限が必要）。psutil による設定で失敗した場合は警告ログでスキップします。

---

## ディレクトリ（主要ファイル／モジュール構成）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py (バージョン情報)
  - config.py — Settings クラス、.env 自動ロード
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - execution_engine.py (エンジン本体、EngineConfig 等)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py / broker_api.py（ブローカー抽象）
    - order_record.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・読み書きラッパ
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
  - data/
    - （実行時に生成される SQLite / DuckDB / flag / pid 等を置くディレクトリ）
  - utils/
    - process_priority.py
  - その他: data 操作用ユーティリティや tests（該当すれば）

（上記は主要ファイルに限定した簡易ツリーです。実際のファイル数やサブモジュールはリポジトリ内を参照してください。）

---

## 実装上の注意事項 / トラブルシューティング

- .env のロード
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。CI／テスト等でロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブル／インデックスを作成します。既存テーブルに対する小さなマイグレーション（列追加）も内包しています。

- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading の際、Execution は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用します。Monitoring は環境にかかわらず sqlite_path（監視 DB）を使用します。

- OpenAI API
  - API 呼び出しはリトライ（指数バックオフ）・レスポンスバリデーション・部分失敗時の保護（部分的な INSERT）等のフェイルセーフ処理があります。OPENAI_API_KEY を設定してください。API 利用時のコスト・レート制限に注意。

- psutil による優先度/affinity 設定
  - プラットフォームによっては権限不足で設定に失敗することがあります（警告ログのみで継続します）。

- ファイルパスと権限
  - data ディレクトリや DB ファイルへのアクセス権限を確認してください。監視プロセスが read-only で DB を開く場合は URI に ?mode=ro を付けるなど制御している箇所があります。

---

## 開発・拡張のヒント

- 研究用関数（research/*.py）は DuckDB 接続を受け取り SQL と Python を組み合わせて実行する設計です。prices_daily / raw_financials 等のテーブルがあればローカルで再現可能です。
- AI モジュール（news_nlp, regime_detector）はテストしやすいように API 呼び出しをラップしたプライベート関数を用意しています。ユニットテスト時はこれらをモックして動作検証が可能です。
- order_manager / reconciler は Broker API を抽象化しているため、ブローカ実装（本番・モック）を追加することで容易に接続先を差し替えられます。

---

この README はコードベースの主要点をまとめたものです。詳しい設計思想やアルゴリズムの背景（PortfolioConstruction.md / StrategyModel.md 等）がプロジェクト内にある想定ですので、そちらも参照してください。必要であればセットアップの詳細手順（requirements.txt / docker 化 / systemd ユニットファイル など）や運用手順のテンプレートも作成します。どの情報がさらに必要か教えてください。