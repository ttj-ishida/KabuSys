# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。この README はリポジトリ内のモジュール群から自動売買／監視／リサーチ／AI 補助機能の使い方・設定・ディレクトリ構成をまとめたものです。

注意: この README は提供されたソースコードを基に作成しています。実際の運用では十分なテストと安全対策（バックアップ、アクセス制御、資金管理等）を行ってください。

---

## プロジェクト概要

KabuSys は日本株自動売買に関する以下の主要機能を備えます。

- Execution: ブローカーへの発注、注文状態管理、リコンシリエーション（再起動時の同期）
- Monitoring: システム状態（CPU/メモリ/ディスク/プロセス）、注文滞留・約定異常、ドローダウン監視、アラート送信（LINE）
- Portfolio Construction: 候補選定・重み計算・ポジションサイズ計算・セクター制限
- Research: ファクター計算（Momentum/Value/Volatility 等）、特徴量解析・IC 計算
- AI 補助: ニュースのセンチメントを LLM（OpenAI）で評価して ai_scores に格納、マクロセンチメントと ma200 で市場レジーム判定
- Tools: Paper Trading の検証レポート生成や Streamlit ダッシュボードなどのユーティリティ

主要な実行スクリプト:
- run_monitoring.py — SystemMonitor のポーリングループ起動
- run_execution.py — ExecutionEngine 起動（KABUSYS_ENV による paper_trading 切替）
- tools/paper_verification_report.py — Paper Trading 検証レポート出力
- monitoring/streamlit_dashboard.py — Streamlit による監視ダッシュボード

---

## 主な機能一覧（抜粋）

- 環境設定管理（.env / .env.local 自動読み込み、Settings クラス）
- DB 管理: SQLite（監視用）と DuckDB（時系列データ・リサーチ用）
- 監視：
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存否、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション数制限、ダッシュボード/リスクログ更新
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件によりデータ/ファイルで ExecutionEngine を停止させるフラグ（data/kill.flag）
- Execution:
  - Broker クライアント抽象化（paper_trading 時は MockBroker）
  - OrderManager / OrderRepository / Reconciler による安全な発注と再同期
  - リスク管理（Rate limit、ポジション上限、ドローダウン等）
- Portfolio:
  - 候補選定、等金額／スコア加重、risk-based サイズ計算、セクターキャップ、レジーム乗数
- Research:
  - DuckDB 上でのファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Spearman rank）計算、統計サマリー
- AI:
  - ニュース記事を LLM（gpt-4o-mini）でスコアリングして ai_scores に保存
  - マクロニュース＋ETF ma200 による市場レジーム判定（bull/neutral/bear）
- ツール:
  - Paper Trading の検証レポート（稼働率・約定率・レイテンシ等）
  - Streamlit ダッシュボードで監視データ可視化

---

## セットアップ手順

前提
- Python 3.10 以上（ソースは PEP 604 の union 型記法などを使用）
- SQLite（Python 標準ライブラリで利用可）
- 推奨: 仮想環境の利用（venv / poetry / pipenv 等）

1. リポジトリのクローン（省略）

2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb psutil requests streamlit openai
   ```
   - 補足: sqlite3 は標準ライブラリで利用できます。
   - 他に実行・テストで必要なパッケージがあればプロジェクトの requirements.txt を参照してください（本コードベースには明示されていません）。

4. プロジェクト構成に合わせて環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
   - 主要な環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
     - KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - .env 例:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=your_openai_key
     LINE_CHANNEL_ACCESS_TOKEN=xxx
     LINE_USER_ID=yyy
     ```

5. データディレクトリの作成（初回）
   ```bash
   mkdir -p data
   ```

---

## 使い方

開発中のディレクトリ構成をそのまま使う場合は、Python の import 検索パスに `src` を追加して実行します。例:

1. 環境変数の設定（例）
   ```bash
   export KABUSYS_ENV=development
   export JQUANTS_REFRESH_TOKEN=...
   export KABU_API_PASSWORD=...
   export OPENAI_API_KEY=...
   ```

2. モニタリングを起動（ポーリングで監視データを収集）
   ```bash
   # プロジェクトルートから
   PYTHONPATH=src python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
   - 起動時にプロセス優先度を high に設定する処理を試みます（権限による失敗は警告でスキップ）。

3. ExecutionEngine を起動（実際の発注処理を行う）
   ```bash
   PYTHONPATH=src python -m kabusys.run_execution
   ```
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して発注は `data/paper_trading.db` に記録され、本番 DB とは分離されます。
   - 設定は Settings クラス（環境変数）で制御されます。

4. Paper Trading 検証レポート（コマンドライン）
   ```bash
   PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # または DB パスを明示
   PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、判定 PASS/FAIL。

5. Streamlit ダッシュボード（監視データの可視化）
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - データベースを読み取り専用で開き、ダッシュボードを表示します。

6. AI 関連（ニューススコアリング / レジーム判定）
   - kabusys.ai.score_news: DuckDB の raw_news / news_symbols / ai_scores を使って LLM スコアを生成して書き込む。OpenAI API キーが必要。
   - kabusys.ai.regime_detector.score_regime: ETF ma200 とマクロニュースでレジーム判定し market_regime テーブルへ書き込み。

注意点:
- Settings は .env / .env.local / OS 環境変数を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring の DB 初期化（テーブル作成・簡易マイグレーション）は init_monitoring_db() により行われます。run_monitoring/run_execution は起動時にこれを呼びます。
- Kill Switch は RiskMonitor の評価結果に基づいて data/kill.flag を作成し、ExecutionEngine に停止を促す仕組みです。

---

## 主要設定（Settings）とデフォルト値

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: ログレベル（INFO 等。Settings.log_level で検証）
- SQLITE_PATH: data/monitoring.db（監視用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- DUCKDB_PATH: data/kabusys.duckdb
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消す（"1" で有効）
- PAPER_FILL_MODE: paper trading の約定挙動（instant|partial|never|reject、デフォルト "instant"）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視のしきい値

---

## ディレクトリ構成（主要ファイル）

以下は提供されたソースの主要ファイルと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理、.env 自動ロード
  - run_monitoring.py — SystemMonitor ポーリングループ起動
  - run_execution.py — ExecutionEngine 起動（paper_trading 切替）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — data/kill.flag 制御
    - monitoring_engine.py — 各 Monitor をまとめたループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ... — 発注・注文管理関連
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算 / 投下資金制約
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントの LLM スコア化（ai_scores 書き込み）
    - regime_detector.py — ma200 + マクロセンチメントで市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のリポジトリにはさらに細かいファイル群が存在します。ここに挙がっていないモジュールも実装されています。）

---

## 運用上の注意・補足

- 安全性: ExecutionEngine は実際に金銭を動かす可能性があるため、本番 (live) 扱い時は API キーや認証情報の管理、権限制御、監視/アラート設定を厳密に行ってください。
- paper_trading モードでは本番 DB とデータが分離され、発注は MockBrokerClient によってローカル DB に記録されます（テスト用）。
- Process priority / CPU affinity の設定は OS に依存し、権限不足で失敗する場合は警告でスキップされます。
- OpenAI へは API 呼び出しを行います。API のエラーは指数バックオフでリトライする実装がありますが、API 利用にはコストが発生します。
- DB マイグレーション: monitoring_db.init_monitoring_db は簡易マイグレーション（列追加判定等）を行いますが、複雑なマイグレーションは手動で対応してください。

---

上記を参考にローカル環境で試し、必要に応じて各モジュールを拡張・組み合わせて運用してください。質問や README の追記希望（例えばインストール用 requirements.txt、実行例のログ出力例等）があれば教えてください。