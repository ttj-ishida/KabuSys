# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
このリポジトリは、取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究・ファクター計算、AIによるニュースセンチメント処理などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- 日次／リアルタイムのシグナルから注文を作成・送信し、リスク管理を行う ExecutionEngine
- システム状態・注文状況・リスク指標をポーリングしてログとアラートを出す Monitoring
- ポートフォリオ候補選定、重み計算、ポジションサイズ計算などの Portfolio 機能（純粋関数）
- DuckDB を用いたファクター計算・リサーチ機能（prices_daily / raw_financials 参照）
- OpenAI を利用したニュースセンチメント（AI モジュール）
- Streamlit ベースの監視ダッシュボード、紙トレード検証レポート生成ツール 等

設計方針として、ルックアヘッドバイアス回避（target_date 等の明示的指定）、DB の分離（paper_trading 用 DB など）、フェイルセーフな API 呼び出し（リトライやフォールバック）を重視しています。

---

## 主な機能一覧

- Execution
  - 証券ブローカーへの注文送信／状態同期（Reconciler）
  - リスク管理（RiskManager）・オーダーマネージャ（OrderManager）
  - paper_trading モード（MockBrokerClient を使用し本番 DB と分離）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス有無／データ鮮度監視
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：フラグファイルを書いて ExecutionEngine を安全停止
  - AlertManager：LINE Push でアラート送信（クールダウンあり）
  - Streamlit ダッシュボード（read-only で監視 DB を表示）
- Portfolio
  - 候補選定（score/order_rank）、等重・スコア重み算出
  - セクター制限、レジーム乗数、ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - ファクター（Momentum / Volatility / Value）計算（DuckDB）
  - 将来リターン、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp：ニュースを集約して OpenAI でセンチメント評価 → ai_scores テーブルへ書込
  - regime_detector：ETF の MA とマクロニュースを組合せて市場レジーム判定
- Tools
  - 紙トレード検証レポート生成スクリプト（tools.paper_verification_report）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワークアクセス（LINE API / OpenAI API 利用時）

requirements ファイルは同梱されていない想定なので、仮想環境を作成して手動でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 設定（環境変数）

Settings クラスは自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数を上書きしない）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（主なもの）:

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- SQLITE_PATH: 監視用 SQLite DB パス — デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB — デフォルト: data/paper_trading.db
- PID_FILE_PATH: ExecutionEngine PID ファイル — デフォルト: data/execution.pid
- KILL_FLAG_PATH: kill.flag のパス — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — デフォルト: 60
- PAPER_FILL_MODE: paper_trading の約定モード — valid: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート用

注意:
- Monitoring の DB 初期化（テーブル作成）は `init_monitoring_db()` で行います。monitoring コンポーネントは本番 sqlite_path を使用します（環境に関わらず）。
- paper_trading モードでは Execution は paper_trading DB を利用して本番 DB と分離されます。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / ワークディレクトリへ移動
2. 仮想環境作成・有効化（例は Unix 系）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
4. `.env`（または `.env.local`）をプロジェクトルートに作成し、必要な環境変数を設定
   - 最低限: KABUSYS_ENV, OPENAI_API_KEY（ai 機能を使う場合）、KABU_API_PASSWORD（実運用）
   - 例:
     ```
     KABUSYS_ENV=paper_trading
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-...
     ```
5. データディレクトリ（`data/`）を作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  - 簡単に起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更（秒）:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は常に本番 sqlite_path を使って監視ログを残します（環境に依らず）。

- 実行エンジン起動（Execution）
  - 本番/開発/紙トレードの動作は `KABUSYS_ENV` に依存します。
  - paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH` に記録します。
    ```bash
    python -m kabusys.run_execution
    ```
  - 実運用（live）では kabuステーション等のブローカークライアントを使用します（環境変数で認証等を設定）。

- 紙トレード検証レポート（コマンドライン）
  - 既存の paper_trading DB を元に集計レポートを出力します。
    ```bash
    python -m kabusys.tools.paper_verification_report
    # 期間を指定
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB を直接指定
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- Streamlit ダッシュボード（監視 DB を閲覧）
  - 監視 DB を読み取り専用で表示します。
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- AI 関連ユーティリティ
  - ニューススコアリング:
    - コード内の `kabusys.ai.news_nlp.score_news(conn, target_date, api_key)` を呼ぶことで ai_scores テーブルへ書き込み可能。
  - レジーム判定:
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)`

---

## 実行時の注意点 / 動作特性

- プロセス優先度: run_monitoring / run_execution の両スクリプトはプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足時は警告が出てスキップされます。
- DB マイグレーション: monitoring DB は起動時にテーブル・インデックスを作成し、必要なカラムがなければ ALTER TABLE で追加（冪等）。
- キルスイッチ: KillSwitch は `KILL_FLAG_PATH`（デフォルト data/kill.flag）へ理由を記したファイルを書き、Execution 停止を促します。ExecutionEngine 側ではこのファイルを検知して停止する仕組みを想定。
- API 呼び出しの堅牢性: OpenAI 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライします。失敗時は安全側のフォールバック値（例: macro_sentiment=0.0）で継続します。
- モード分離: paper_trading は本番 DB と完全分離する設計です。実データを汚さないように注意してください。

---

## ディレクトリ構成（主なファイル）

（リポジトリのルートに `src/` があり、その下にパッケージ `kabusys`）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env の読み込みと Settings
  - run_monitoring.py  — SystemMonitor のポーリング起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py    — monitoring 用 SQLite 層（テーブル作成・CRUD）
    - system_monitor.py   — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py    — 注文滞留・約定異常検出
    - risk_monitor.py     — ドローダウン / ポジション上限監視
    - kill_switch.py      — フラグファイルによる停止シグナル
    - alert_manager.py    — LINE Push アラート
    - monitoring_engine.py— 監視コンポーネントの束ね
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - risk_manager.py
    - ...（注文管理・ブローカ抽象化）
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
  - data/
    - pipeline.py
    - stats.py
    - ...（DuckDB テーブル読み書きヘルパ）
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py

---

## 開発 / テストのヒント

- Settings はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動読み込みを無効化できます。
- OpenAI 呼び出しやブローカー API 呼び出しはテストでモックしやすいように設計されています（内部の API 呼び出し関数を patch して振る舞いを制御可能）。
- MonitoringDB / Monitoring クラス群は比較的副作用が限定されており、単体テストが書きやすい構造です。
- DuckDB を使った research モジュールは SQL クエリを直接発行しているため、テスト用に小さな DuckDB を作成してデータを投入すると良いです。

---

## ライセンス / 責務

この README はコードベースに基づく簡易ドキュメントです。運用環境での実行・資金投入前にコードの安全性・ロジック・API 呼び出し部分を十分に監査してください。実運用に伴うリスク（市場リスク・API レート制限・取引手数料等）は自己責任です。

---

必要であれば、以下の点について詳細ドキュメントを追加します：
- 各環境変数の完全な一覧と意味（デフォルト値含む）
- ExecutionEngine の内部フロー（リスク管理設定、EngineConfig）
- BrokerClient の実装方法と MockBroker の仕様
- テスト手順と CI 設定例

どの項目を優先して詳述しますか？