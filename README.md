# KabuSys

KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。本リポジトリには以下の主要機能が含まれます:

- 注文の作成・送信・リコンシリエーションを行う Execution Engine
- システム稼働・注文状態・リスクを監視する Monitoring 系コンポーネント（監視ログは SQLite に永続化）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、セクター制限）
- DuckDB を用いたファクター計算・リサーチツール
- OpenAI を用いたニュース NLP（銘柄別センチメントスコア）および市場レジーム判定
- Paper Trading 向け分離 DB / MockBroker を用いた検証サポート
- Streamlit ベースの監視ダッシュボード、検証レポート生成スクリプト 等

注意: 本 README は提供されたソースコード群に基づく概要と利用手順をまとめたものです。実運用では API キーやブローカー資格情報の管理を慎重に行ってください（本番モードでは本物の発注が行われる想定です）。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 状態同期 / リコンシリエーション（Reconciler）
  - RiskManager による数量制限やサーキットブレーカー（設計上のパラメータあり）
  - Paper Trading モードでは MockBrokerClient を使い、paper_trading 用の SQLite に記録（本番 DB と分離）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度
  - TradeMonitor: 滞留注文（stale orders）・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視と kill.flag 発行
  - AlertManager: LINE Messaging API による一方向プッシュ通知（クールダウン制御あり）
  - MonitoringEngine: 各モニタを纏めて定期ポーリング
  - Streamlit ダッシュボードで監視データ閲覧
- Portfolio
  - 候補選定（スコア降順）、等比配分・スコア比重配分、リスクベース位置決め、単元株丸め、セクター上限適用、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等
- AI
  - ニュース集約 → OpenAI（gpt-4o-mini）で銘柄別センチメント評価 → ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA200 に基づく market regime 判定
- Tools
  - paper_verification_report: Paper Trading の検証レポートを SQLite から生成

---

## 必要な依存ライブラリ（代表例）

本リポジトリのコードから想定される主要依存ライブラリ例:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他（プロジェクトで利用される追加パッケージがあれば requirements.txt を参照）

requirements.txt がない場合は上記を pip でインストールしてください。例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際のプロジェクトでは requirements.txt を用意することを推奨します）

---

## 環境変数 / 設定

Settings は環境変数（またはプロジェクトルートの .env / .env.local）から読み込みます。自動ロード挙動:

- OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑制できます
- プロジェクトルートは .git または pyproject.toml を起点に探索します

主要な環境変数（抜粋）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: paper トレードの fill 挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用

例: .env の最低サンプル

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
```

2. 依存パッケージをインストール

```bash
pip install duckdb psutil requests openai streamlit
```

3. 必要なディレクトリを作成

```bash
mkdir -p data
```

4. 環境変数を設定（.env/.env.local をプロジェクトルートに作成）  
   参考: 上記 .env サンプルを参照

5. （任意）Paper Trading 用 DB を初期化するには、Execution スクリプトを paper_trading モードで実行すると必要テーブルが作成されます（init_monitoring_db を利用）。

---

## 実行方法 / 使い方

主要なエントリポイントはモジュールとして実行できます。

- Monitoring（常駐ポーリング）を起動

```bash
python -m kabusys.run_monitoring
# もしくは
KABUSYS_ENV=development MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

挙動:
- プロセス優先度を "high" に設定しようとします（psutil により OS に依存）
- Settings の sqlite_path（監視 DB）と duckdb_path に接続し、監視テーブル群を初期化します
- SystemMonitor.check_once を指定間隔で実行（デフォルト 60 秒）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能

- Execution Engine（実行セッション）を起動

```bash
python -m kabusys.run_execution
# Paper Trading モード
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します
- ExecutionEngine、OrderManager、RiskManager、Reconciler を組み立ててセッションを実行します
- 起動時に Reconciler により未解決の注文やポジション差分の自動リコンを試みます

- Paper Trading 検証レポート生成

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit 監視ダッシュボード

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI 系（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です
  - 関数を呼び出す（プログラム内から）:
    - kabusys.ai.score_news(...) — ai_scores に書き込み
    - kabusys.ai.regime_detector.score_regime(...) — market_regime テーブルへ書き込み

注意事項:
- 本番モード（KABUSYS_ENV=live）では外部ブローカーに対して実際に発注が行われる前提です。十分に検証した上で運用してください。
- Paper Trading モードでは DB 分離と MockBroker による安全な検証が行われますが、挙動は設定に依存します（PAPER_FILL_MODE など）。

---

## よく使う環境変数（要約）

- KABUSYS_ENV=development|paper_trading|live
- OPENAI_API_KEY=（AI機能用）
- JQUANTS_REFRESH_TOKEN=（データ取得用）
- KABU_API_PASSWORD=（発注 API）
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- DUCKDB_PATH=data/kabusys.duckdb
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- MONITOR_POLL_INTERVAL=60
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

---

## ディレクトリ構成（該当ソースファイルの抜粋）

リポジトリ内の主なモジュールとファイル（提供されたコードに基づく）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みと Settings
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）→ ai_scores 書き込み
    - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — monitoring DB テーブル初期化 + MonitoringDB ラッパ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — kill.flag 書込み（ExecutionEngine 停止シグナル）
    - alert_manager.py — LINE API 送信ラッパ
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - order_manager.py — 注文の生成・送信・状態遷移
    - reconciler.py — 起動時リコンシリエーション
    - （その他ブローカーインターフェース / order_repository などは別ファイルに実装想定）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — momentum/volatility/value 等のファクター算出（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は提供されたコードファイルの抜粋です。実際のリポジトリではさらに execution/broker_api などの補助モジュールが存在する可能性があります。）

---

## 運用上の注意 / ベストプラクティス

- 本番口座の操作前に Paper Trading モードで十分に検証してください。Paper Trading は DB を分離しているため安全です。
- API キーやパスワードは .env/local に保存する場合、アクセス権限を適切に設定してください。公開リポジトリにキーを含めないでください。
- Monitoring は kill.flag による停止シグナルをサポートします（kill.flag を作成すると ExecutionEngine が安全に停止する）。
- OpenAI 等外部 API 呼び出しはレート制限や失敗を考慮したリトライ/フォールバック設計になっていますが、運用時はコスト・レート制限を監視してください。
- psutil を使ってプロセス優先度を変更します。権限不足で失敗する場合があるためログを確認してください。

---

この README は提供されたソース群から要点を抜粋・整理したものです。追加のセットアップ手順（requirements.txt、DB 初期データ投入スクリプト、ブローカーの具体的実装等）はプロジェクトの配布元ドキュメントを参照してください。必要であれば、README を補完する具体的なコマンドや設定例を追記します。