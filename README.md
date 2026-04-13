# KabuSys

日本株向け自動売買システムの一部（ライブラリ・運用ツール群）。  
本リポジトリには取引実行・監視・リサーチ・ポートフォリオ構築・AI（ニュースセンチメント／レジーム判定）などのモジュールが含まれます。

---

## 概要

KabuSys は次のような機能を目的としたモジュール群です：

- 注文作成・送信・状態同期（ExecutionEngine, OrderManager, Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と通知（LINE）
- Paper Trading 環境（MockBroker を使用して本番 DB と分離）
- データ解析／リサーチ（DuckDB を使ってファクター計算や特徴量解析）
- ニュースの LLM によるセンチメントスコア化（OpenAI）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

設計上の注意点：
- 環境ごとの分離（`KABUSYS_ENV`：`development | paper_trading | live`）をサポート
- 環境変数は .env / .env.local から自動読み込み（プロジェクトルートが .git または pyproject.toml を基準）
- Paper trading はデータベースを分離して本番 DB を汚さない設計

---

## 主な機能一覧

- 実行系
  - 注文生成・重複チェック（OrderManager）
  - ブローカー同期・再構築（Reconciler）
  - Risk 管理（RiskManager、各種制限設定）
- 監視系
  - システム状態監視（CPU / メモリ / ディスク / PID）
  - 注文滞留・約定異常検知
  - ドローダウン／ポジション上限監視と kill.flag 発行
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード表示
- ポートフォリオ構築
  - 候補選定・重み計算（等金額・スコア加重）
  - セクターキャップ適用・レジーム乗数
  - 株数算出（単元株丸め、aggregate cap 等）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI（LLM）
  - ニュースの銘柄別センチメント算出（OpenAI）
  - マクロ＋ETF MA200 で市場レジームを判定（OpenAI optional）
- 運用ツール
  - 継続的監視ループ起動スクリプト
  - ExecutionEngine 起動スクリプト（Paper Trading 対応）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ

必要な主な Python パッケージ（代表例）：
- duckdb
- psutil
- openai
- requests
- streamlit

推奨：仮想環境を作ってからインストールしてください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

環境変数（代表的なもの）:  
- 必須（実行環境で必要に応じて設定）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY
- オプション / デフォルトがあるもの
  - KABUSYS_ENV — development / paper_trading / live （default: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（default: data/paper_trading.db）
  - PAPER_FILL_MODE — paper trading の約定モード（instant/partial/never/reject）
  - PID_FILE_PATH — execution.pid（default: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag（default: data/kill.flag）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト 60）

.env の自動読込み:
- プロジェクトルート（.git か pyproject.toml が基準）に `.env` / `.env.local` がある場合、自動で読み込みます。
- OS 環境変数が優先されます。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。

注意:
- Paper Trading 実行時は sqlite ファイルが `PAPER_TRADING_SQLITE_PATH` に書き込まれ、本番用 `SQLITE_PATH` とは分離されます。

---

## 使い方（主なコマンド）

1. ExecutionEngine を起動（本番 or paper_trading に依存）
```bash
# production 例（環境変数を設定してから）
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

Paper trading（MockBroker）で起動する例:
```bash
export KABUSYS_ENV=paper_trading
# optional: export PAPER_FILL_MODE=instant
python -m kabusys.run_execution
```

2. 監視ループ起動
```bash
# デフォルト 60秒間隔。MONITOR_POLL_INTERVAL で上書き可能
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 監視は環境設定にかかわらず本番の sqlite_path を使用して `monitoring.db` にログを書きます（監視 DB は本番 DB を使う想定）。
- 監視起動時にプロセス優先度を "high" に変更する処理が走ります（権限により失敗しても続行します）。

3. Streamlit ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

4. Paper Trading 検証レポート
```bash
# デフォルト DB は data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db で別 DB を指定可能
```

5. AI 機能（スクリプト／プログラムから呼び出す）
- ニューススコア算出: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

これらは OpenAI API キー（環境変数 `OPENAI_API_KEY` または引数）を必要とします。API 呼び出しはフォールバック・リトライや失敗時の安全策を組み込んでいます（失敗時はゼロ点やスキップを行う設計）。

---

## 重要なファイル / パス（デフォルト）

- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill フラグ: data/kill.flag

環境変数でパスを上書きできます（`DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` / `PID_FILE_PATH` / `KILL_FLAG_PATH`）。

---

## トラブルシューティング（よくある注意点）

- 権限関連：プロセス優先度や CPU affinity の設定は権限により失敗することがあります（警告ログが出てスキップされます）。
- DB ロック：SQLite を複数プロセスで書き込む際はロックに注意。監視は同じ monitoring DB に書き込みます。
- OpenAI 呼び出し：API キー未設定だと例外を投げます（AI 機能呼び出し前に設定してください）。レート制限等のエラーはリトライロジックあり。
- kill.flag：ExecutionEngine 停止のために kill.flag を書き込む仕組みがあります。必要に応じて `KILL_FLAG_CLEAR_ON_START=1` を使って起動時に自動クリアできます。

---

## ディレクトリ構成

以下は主要ファイルを抽出したツリー（src/kabusys 以下）です：

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数／設定管理
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite テーブル定義 + MonitoringDB ラッパー
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
    - (その他 broker / engine / repository 関連)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - data/
    - (データパイプライン / stats 等のモジュール — DuckDB を参照)
  - utils/
    - __init__.py
    - process_priority.py

（実際のリポジトリにはさらに細かいモジュールや補助クラスが含まれます。）

---

## サンプル .env（最小例）

.env.example を参考にしてください。最小の例：
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_TOKEN
KABU_API_PASSWORD=YOUR_KABU_PASSWORD
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
```

---

## 開発・拡張のヒント

- DuckDB 接続を渡すことでリサーチ関数（factor_research 等）は外部に影響を与えず計算できます。テストしやすい純粋関数が多く設計されています。
- AI 呼び出し部は外部関数（_call_openai_api）を patch してテストするように設計されています。
- MonitoringDB はビジネスロジックを持たない CRUD 層に分離されており、監視ロジックは MonitoringDB を利用しているため差し替えが容易です。

---

README で触れていない内部仕様や API の詳細が必要であれば、どのモジュール（ex. OrderManager / Reconciler / news_nlp / position_sizing）のドキュメントを詳しく作成するか教えてください。