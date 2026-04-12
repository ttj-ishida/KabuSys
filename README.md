# KabuSys

日本株向けの自動売買／リサーチ／監視フレームワーク（軽量プロトタイプ）。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ファクタ計算・リサーチ、AI ベースのニュースセンチメント評価などを含むモジュール群で構成されています。

---

## 概要

KabuSys は以下の目的で設計されています。

- 戦略からのシグナルに基づく注文作成・送信・状態管理（Execution）
- 実行プロセスと発注状況の監視（Monitoring）
- ファクター計算や特徴量探索などのリサーチユーティリティ（Research）
- ニュースを LLM（OpenAI）でスコアリングして投資判断に活用（AI）
- Paper Trading（検証用の完全分離された DB）をサポート

設計方針の特徴：

- DuckDB を用いたファクター集計（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ（monitoring.db）および（環境に応じて）Paper Trading 用 DB
- OpenAI（gpt-4o-mini）を用いたニュース／マクロセンチメント評価（フェイルセーフ設計）
- OS 環境変数や .env/.env.local による設定管理（自動ロード機能あり）

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine（ブローカー抽象化を介した発注・状態遷移管理）
  - Reconciler による再起動時の自動復旧（未送信・不整合の突合せ）
  - Paper trading モード（KABUSYS_ENV=paper_trading）で本番と完全分離
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、プロセス存在、データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch：条件に応じた停止フラグ (data/kill.flag) の書き込み
  - AlertManager：LINE へのプッシュ通知（クールダウン管理付き）
  - Streamlit ダッシュボード（data/monitoring.db の可視化）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）等の統計分析ユーティリティ
- AI
  - news_nlp.score_news：ニュースを集約して OpenAI で銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime：ETF（1321）MA200 乖離＋マクロニュースで市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading の検証レポート生成

---

## 事前準備 / セットアップ

必要要件（目安）：

- Python 3.9+（型注釈やモジュールの動作から）
- pip による以下主要パッケージ（実行環境に合わせて requirements.txt を用意する想定）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

例（仮の requirements のインストール）:
```bash
pip install duckdb psutil requests openai streamlit
```

環境変数と .env の自動読み込み:

- リポジトリルートに `.env` / `.env.local` を置くと、自動で読み込まれます（OS 環境 > .env.local > .env の優先順）。
- 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（運用時）環境変数（一部）:

- JQUANTS_REFRESH_TOKEN — J-Quants API（必要に応じて）
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API 利用時に必須（AI モジュール）
- その他（任意）:
  - PAPER_FILL_MODE（paper_trading 時の模擬約定方式: instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB path, default: data/paper_trading.db）
  - SQLITE_PATH（監視 DB path, default: data/monitoring.db）
  - DUCKDB_PATH（duckdb path, default: data/kabusys.duckdb）
  - KABUSYS_ENV（development|paper_trading|live, default: development）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）

データディレクトリ作成（必要に応じて）:
```bash
mkdir -p data
```

初回起動時、実行スクリプト側で monitoring DB の初期化（テーブル作成 / マイグレーション）が自動的に行われます（init_monitoring_db）。

---

## 使い方

基本的なエントリポイント（パッケージモジュールとして実行）:

- 実行エンジンを起動（ExecutionEngine）
  - Paper Trading: KABUSYS_ENV=paper_trading を指定すると mock ブローカーと専用 DB を使用
```bash
# 本番相当 or development
python -m kabusys.run_execution

# Paper trading モード
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- 監視プロセスを起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60）
```bash
python -m kabusys.run_monitoring
# 例: 30秒ごとにポーリング
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Paper Trading 検証レポートを生成
```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定と DB 指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

- Streamlit ダッシュボード（監視）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI モジュールの利用（ライブラリ関数として）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも DuckDB 接続（duckdb.connect(... )）を渡して呼び出します。api_key 引数を省略すると環境変数 OPENAI_API_KEY を参照します。

注意点：

- run_execution はプロセス優先度を "high" に設定し、PID ファイル（デフォルト data/execution.pid）を用いて ExecutionEngine の実行状態を表現します。
- run_monitoring は本番の sqlite_path（監視 DB）を環境に関わらず使用します（監視ログは本番 DB を参照）。
- Paper Trading モードでは monitoring 用 DB と発注用 DB を分離（data/paper_trading.db）します。

---

## よく使うファイル / コマンドまとめ

- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## ディレクトリ構成

（src 以下を基準とした主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings 管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（ブローカー API 抽象・実装）
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマと永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - research/
    - factor_research.py     — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し（銘柄別スコア）
    - regime_detector.py     — マクロ + MA200 を合成してレジーム判定
  - data/                    — デフォルト DB 保存先（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/monitoring_db.py contains schema and helpers. (already listed)

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: 監視 DB パス（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の模擬約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必要な場合）
- KABU_API_PASSWORD: kabuステーション API password
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効にする

---

## 運用上の注意

- Paper Trading モードは本番 DB と完全に分離するよう設計されています。実運用の際は必ず KABUSYS_ENV の設定を確認してください。
- OpenAI を利用する処理は外部 API 依存のため、API エラー時はフェイルセーフ（0.0 フォールバックやスキップ）を行う設計です。ただし API キーは必ず管理してください。
- run_execution / run_monitoring はプロセス優先度設定や PID / kill.flag を使った監視連携を行います。適切な権限（nice の設定等）が必要な場合があります。
- monitoring_db のスキーマは init_monitoring_db で冪等に作成・マイグレーションされます。既存 DB に対して一部カラム追加のマイグレーションを行うコードを含みます。

---

## 開発者向けメモ

- DuckDB 接続は各モジュールに注入して使用します（ユニットテストでは in-memory やテスト用ファイルを使ってください）。
- OpenAI 呼び出しはテスト時にパッチ可能な設計（_call_openai_api をモック）です。
- .env パーサーはシェル形式（export を含む）の行やクォート・エスケープに対応しています。

---

必要であれば README に以下の追記が可能です：
- requirements.txt の具体的な内容
- systemd / supervisor でのサービス定義サンプル
- CI / テスト実行方法
- DB スキーマの詳細ドキュメント

追加したい内容があれば教えてください。