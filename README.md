# KabuSys

日本株向け自動売買フレームワークの一部（実行エンジン、監視、リサーチ、AI 補助など）。  
このリポジトリは主に以下のサブシステムで構成されています。

- execution: 発注エンジン、注文管理、リコンシリエーション、リスク管理
- monitoring: システム監視・アラート・ダッシュボード・キルスイッチ
- portfolio: 銘柄選定・配分・ポジションサイジング・リスク調整
- research: ファクター計算・特徴量探索
- ai: ニュース NLP（OpenAI を利用）・市場レジーム判定
- utils / config: 設定読み込み・プロセス優先度ユーティリティ等

この README ではプロジェクト概要、機能一覧、セットアップ手順、主要コンポーネントの使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群です。主な目的は次のとおりです。

- 売買シグナルに基づく注文の作成・送信（ExecutionEngine）
- 発注後の約定同期・リコンシリエーション（Reconciler）
- リスク管理（Gate チェック、サーキットブレーカー、ドローダウン監視）
- システム稼働状態・注文/約定・ポジションを監視・永続化（Monitoring）
- ニュースを LLM（OpenAI）で評価し、銘柄別センチメントを生成（AI）
- DuckDB を用いた価格・財務データに対するファクター計算（Research）
- PortfolioConstruction に基づく候補選定とポジション決定（Portfolio）

設計方針の要点：
- DB（SQLite / DuckDB）を用いて状態を永続化
- 外部 API（ブローカー・OpenAI）は抽象化してテスト可能に設計
- ルックアヘッドバイアス回避のため日付参照に注意
- フェイルセーフ（API失敗時はゼロ値で継続等）

---

## 主な機能一覧

- Execution
  - Signal から注文を作成、OrderManager を経由して Broker API に送信
  - クラッシュ耐性を考慮した二相永続化（OrderSent/OrderAccepted）
  - Reconciler による起動時の自動復旧（OrderSent 照合、ポジション差分検知）
  - リスク管理（Gate1/2/3、レートリミット、サーキットブレーカー）
  - Paper trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限検知、dashboard 更新
  - KillSwitch: 条件を満たしたらフラグファイルを書いて ExecutionEngine に停止シグナル
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（read-only）で監視データ可視化

- Research / AI
  - DuckDB 上でのモメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン・IC（スピアマン）算出、ファクター要約
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に保存
  - 市場レジーム判定（ETF ma200 とマクロ記事の LLM センチメントを合成）

- Utilities
  - 設定管理（.env / 環境変数の読み込み・Settings クラス）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - DB 初期化スクリプト（監視用テーブル作成）

---

## セットアップ手順

前提:
- Python 3.10 以上（| タイプヒントなどを使用）
- SQLite, DuckDB を使用（DuckDB Python パッケージ）
- ネットワーク接続が必要（OpenAI, LINE, Broker API などを利用する場合）

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- requests
- streamlit

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai requests streamlit
```

環境変数 / .env:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（抜粋）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時に必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading モード時の専用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の成行/約定挙動）
- PID_FILE_PATH, KILL_FLAG_PATH（デフォルト: data/execution.pid / data/kill.flag）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）

簡易 .env 例:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
JQUANTS_REFRESH_TOKEN=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

DB 初期化:
- 監視用の SQLite テーブルはスクリプト起動時に自動作成されます（init_monitoring_db）。
- DuckDB のスキーマ（prices_daily, raw_financials 等）は別途作成・ロードしてください（このリポジトリに含まれていない場合があります）。

---

## 使い方

プロジェクトをパッケージとしてインポートして使えますが、典型的な起動・操作例を示します。ローカル開発では `PYTHONPATH=src` を使うかパッケージインストールしてください。

環境を一時的に指定してスクリプトを実行する例:
```bash
# PYTHONPATH 指定で直接スクリプトを実行（開発環境向け）
PYTHONPATH=src python src/kabusys/run_monitoring.py
PYTHONPATH=src python src/kabusys/run_execution.py

# またはパッケージとして実行（パッケージ化/インストール後）
python -m kabusys.run_monitoring
python -m kabusys.run_execution
```

監視ループ（run_monitoring.py）
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- 監視は Settings にかかわらず本番 sqlite_path（SQLITE_PATH）を使用する設計。
- 起動時にプロセス優先度を "high" に設定しようとします（失敗しても続行）。

実行エンジン（run_execution.py）
- KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient が使用され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使って完全に分離された動作をします。
- 起動時にプロセス優先度を "high" に設定します。
- ExecutionEngine はリコンシリエーション、シグナル処理、プッシュドレインを行います。

Streamlit ダッシュボード
- 監視データを read-only で可視化できます。
```bash
# ドキュメント内にある起動例（監視 DB を指定）
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

AI 機能
- ニュース NLP（kabusys.ai.news_nlp.score_news）は OpenAI API キーが必要です（引数または環境変数 OPENAI_API_KEY）。
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）も OpenAI を使う場合は API キーが必要です。API の失敗時は安全側にフォールバックする設計です。

kill.flag / PID
- ExecutionEngine は起動時に PID をファイルに書くことが想定されています（Settings.pid_file_path）。
- KillSwitch は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込み、エンジン停止を促します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START 設定でフラグのクリア動作を制御できます。

開発向けヒント
- .env / .env.local の読み込み順: OS 環境 > .env.local > .env。自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 単体関数（portfolio, research, ai の一部）は DuckDB 接続や純粋データを渡せば単体テストしやすいように設計されています。

---

## 主要ファイル / 実行スクリプト

- src/kabusys/run_monitoring.py — SystemMonitor のポーリングループ起動
- src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/monitoring/streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
- src/kabusys/config.py — 環境変数 / .env 管理（Settings クラス）
- src/kabusys/ai/news_nlp.py — ニュース NLP（OpenAI）による銘柄センチメント
- src/kabusys/ai/regime_detector.py — 市場レジーム判定（ETF ma200 + LLM）
- src/kabusys/monitoring/* — 監視関連（DB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager）
- src/kabusys/execution/* — 発注関連（ExecutionEngine, OrderManager, Reconciler など）
- src/kabusys/portfolio/* — ポートフォリオ構築ロジック（選定・重み・サイズ・リスク調整）
- src/kabusys/research/* — DuckDB ベースのファクター計算・解析

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py
    run_monitoring.py
    run_execution.py
    utils/
      __init__.py
      process_priority.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      execution_engine.py
      order_manager.py
      reconciler.py
      order_repository.py            # （リポジトリの一部として参照）
      order_record.py
      broker_api.py
      broker_factory.py
      risk_manager.py
      ...
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    data/
      ...  # prices_daily, raw_financials 等を扱うモジュール（実データは別途用意）
```

（注）実際のファイル群は上記以外にもあり得ます。ここでは主要なモジュールを抜粋しています。

---

## 注意点 / 運用上のポイント

- KABUSYS_ENV が `paper_trading` の場合、run_execution は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離されます。必ず運用目的に応じて KABUSYS_ENV を設定してください。
- run_monitoring は Monitoring 用 SQLite（SQLITE_PATH）を使用します。Monitoring は「環境にかかわらず本番 sqlite_path を使う」設計である点に注意してください（`run_monitoring.py` のドキュメント）。
- OpenAI を使う機能は API コストとレート制限に注意してください。score_news / score_regime はリトライ・バックオフ等を実装していますが、運用ルールの整備を推奨します。
- PID ファイル / kill.flag を使った制御はファイルシステムに依存します。監視プロセスと実行プロセスが同一マシンで運用される想定です。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は外部で準備する必要があります（このリポジトリでの生成は別途）。Research/AI の関数は DuckDB 接続を受け取る設計です。

---

必要に応じて、この README をベースに導入手順やデプロイ手順（systemd ユニット例、Dockerfile、CI 設定等）を追加できます。運用環境やブローカー実装の詳細が分かれば、より具体的な運用ガイドを作成します。必要なら教えてください。