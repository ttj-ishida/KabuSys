# KabuSys

日本株向け自動売買システムの一部コンポーネント群（モニタリング / 実行エンジン / 研究・ポートフォリオ構築・AI 補助）をまとめたリポジトリ。  
この README はソースツリーから生成可能な主要機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主に以下を目的としています。

- ExecutionEngine：発注、注文管理、リスク制御、リコンシリエーションを行う実行基盤
- Monitoring：実行エンジンの稼働状況・データ鮮度・注文状態・リスクを監視しログ・アラートを出力
- Portfolio：銘柄選定・重み付け・単元丸めなどのポートフォリオ構築ユーティリティ
- Research：DuckDB の市場データを用いたファクター計算・特徴量解析
- AI：ニュースを LLM（OpenAI）で評価し、マクロレジーム判定やニュースセンチメントを生成
- Tools：Paper Trading 検証レポート生成などのユーティリティスクリプト

設計上の特徴：
- DuckDB（時系列市場データ）、SQLite（監視ログ・発注ログ）を使用
- 本番実行と Paper Trading を分離（環境変数 KABUSYS_ENV）
- OpenAI を用いた NLP モジュールはフェイルセーフ設計（API 失敗時は安全側にフォールバック）
- .env / .env.local による柔軟な設定ロード（自動ロードは無効化可）

---

## 主な機能一覧

- Execution
  - 発注作成、Order 状態遷移管理（OrderManager）
  - ブローカーとの同期・再起動後のリコンシリエーション（Reconciler）
  - RiskManager による発注制御（設定による最大保有比率・利用率等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、実行プロセス存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウンやポジション上限の監視とリスクログ記録
  - KillSwitch：重大トリガー（ドローダウン等）で ExecutionEngine 停止フラグを書き込み
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視ダッシュボード）
- Portfolio
  - 候補選定、等重/スコア重み付け、セクターキャップ適用、ポジションサイズ計算
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - ニュース NLP（銘柄別センチメントを OpenAI で算出し ai_scores へ書き込み）
  - レジーム判定（ma200 とマクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（orders / monitoring データから各指標を集計）

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントに依存）
- Rust 等のビルドは不要（純 Python）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限次をインストール）
     - pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルートに `.env` を置くか、環境に直接設定してください。
   - 自動ロードはデフォルトで有効（config.py がプロジェクトルートを検出した場合 .env / .env.local を読み込み）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成
   - data/ ディレクトリを作成してください（SQLite / PID / フラグファイル格納用）
     - mkdir -p data

6. 初期 DB 作成
   - Monitoring 用 SQLite はスクリプト起動時に自動初期化します（init_monitoring_db）。特別な手順は不要です。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード（instant | partial | never | reject）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（詳細は src/kabusys/config.py を参照）

サンプル .env（最小）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方（起動・主要コマンド）

基本的に各モジュールはモジュール実行可能（if __name__ == "__main__"）になっています。

1. 監視ループ（Monitoring）
   - モニタープロセスを起動（ポーリングして system/trade/risk をチェック）
   - 実行:
     - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL：ポーリング間隔（秒、デフォルト 60）
   - 停止:
     - プロジェクトルートの data/stop_requested.flag を作成するとループが検知して停止します。

2. 実行エンジン（ExecutionEngine）
   - ExecutionEngine を起動して発注セッションを開始
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に分離保存
     - 実行中は data/execution.pid に PID を書き込み、stop フラグ（data/stop_requested.flag）で停止可能
   - 停止:
     - data/stop_requested.flag を作成することで起動中エンジンへ停止命令が伝播します。

3. Streamlit ダッシュボード（監視可視化）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 読み取り専用で監視 DB を表示。MonitoringEngine が生成するデータを参照します。

4. Paper Trading 検証レポート生成
   - 使用例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で変更可）
   - 出力:
     - 稼働率、注文成功率、送信率、レイテンシ指標、総合判定 PASS/FAIL を標準出力へ表示

5. AI モジュール（ニュース NLP / レジーム判定）
   - プログラムから直接呼び出して使用します（関数 API を提供）
     - kabusys.ai.score_news (ラッパーは __init__ でエクスポート)
   - 例（スクリプト内呼び出し）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="sk-...")
   - 注意:
     - OPENAI_API_KEY が必須（引数で渡すことも可）
     - API エラー時は部分フォールバック（スコア0.0）で安全に継続する設計

6. 設定読み込みの挙動
   - config.Settings による集中管理（プロパティ経由で安全に取得）
   - .env / .env.local はプロジェクトルートを自動検出して読み込み（必要に応じて上書き順を制御）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

---

## 運用上のポイント

- Paper Trading と 本番 DB を分離:
  - KABUSYS_ENV=paper_trading により paper_sqlite_path を使用。実データと完全に分離することが可能です。
- 停止・緊急停止:
  - KillSwitch はドローダウンやポジション上限など重大条件を検知すると data/kill.flag を書き込む設計。Execution 側はフラグを検出して安全に停止する想定です。
  - 開発中は stop_requested.flag を作成して run_monitoring / run_execution のループを停止できます。
- 権限・優先度:
  - 起動時にプロセス優先度を set_process_priority("high") で設定しようとします（psutil による処理。権限により失敗しても警告を出力して継続）。
- ログ:
  - ロギングは基本 INFO レベル。Settings.log_level で検証できます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等で実行され、既存 DB に必要カラムが無ければ ALTER TABLE で追加します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

サブパッケージ:
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 broker/engine/repository 関連モジュール)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

その他:
- data/ (SQLite, DuckDB, PID, フラグファイルを配置する想定)
  - monitoring.db (デフォルト)
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 開発・テストのヒント

- 単体関数は副作用が少ない実装になっている（portfolio/*, research/* 等は純粋関数）ためユニットテストが容易です。
- AI 呼び出し箇所（news_nlp._call_openai_api や regime_detector._call_openai_api）は簡単にモック可能（unittest.mock.patch 推奨）。
- MonitoringDB / MonitoringDB クラスは SQLite 接続を受け取りロギングを行うため、テスト時は一時ファイルや :memory: を使用して検証できます。
- streamlit ダッシュボードは監視 DB を読み取り専用で開くため、監視プロセスと同時稼働していても安全に参照できます。

---

この README はソースコード（src/kabusys 以下）を元に作成しました。詳細な API、パラメータ、追加の実行オプションは各モジュールの docstring（ソース内コメント）を参照してください。必要であれば起動例や .env.example を追記しますので教えてください。