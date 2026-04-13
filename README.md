# KabuSys

日本株向けの自動売買・リサーチ基盤の一部をまとめたリポジトリです。  
このREADME はコードベース（src/kabusys 以下）に基づき、プロジェクトの概要、機能、セットアップ・起動方法、主要な設定、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、監視（Monitoring）、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュース評価・レジーム判定、ポートフォリオ構築ユーティリティなどを含むモジュール群です。  
設計方針として、以下を重視しています。

- 本番・ペーパー取引の分離（paper_trading 環境では専用 DB を使用）
- DuckDB をデータ分析（prices_daily / raw_financials など）に使用
- SQLite を監視・トレードログ保存に使用
- LLM（OpenAI）を使ったニュースのセンチメントやマクロセンチメント評価（オプション）
- フェイルセーフ（API 失敗時のフォールバック、冪等な DB 書き込み等）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの切替（本番 / Mock（paper_trading））
  - OrderManager / OrderRepository / Reconciler（起動時の自動リコンシリエーション）
  - リスク管理（RiskManager）を含む発注処理フロー

- Monitoring
  - SystemMonitor: プロセス・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor: 未処理注文（滞留）・約定価格異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視、ダッシュボード集計更新
  - MonitoringEngine: 複数モニタのポーリングとアラート送信
  - AlertManager: LINE Push を使った通知送信
  - Streamlit ダッシュボード（streamlit_dashboard.py）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- Portfolio Construction
  - 候補選定、等重・スコア重み付け、セクター制約、ポジションサイズ計算

- AI（OpenAI）
  - ニュース NLP による銘柄ごとのセンチメント評価（news_nlp）
  - レジーム判定（regime_detector）: ma200 とマクロニュースセンチメントの合成

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクト固有の requirements.txt があればそれを使用してください）

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に .env / .env.local を置くことで自動読み込みされます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番接続時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 使い方（起動例）

※ 下記はリポジトリルートでの実行を想定しています。src 配下がパッケージとして import 可能であること（例えば PYTHONPATH を設定）を前提にしてください。

- 監視ループを起動（SystemMonitor の定期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine を起動（売買エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を用い、paper_trading 用 DB（data/paper_trading.db）を使います

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視データ / ポジション / 注文ログを参照できます（監視 DB が存在しない場合はエラー表示）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または単一引数で --db を指定して別 DB を参照可能

- AI / レジーム・ニューススコアの呼び出し（スクリプト化または import）
  - news scoring: kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
  - regime scoring: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

---

## 注意点 / 運用メモ

- paper_trading モードでは本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します。ローカルでバックテストや検証を行う際はこのモードを推奨します。
- OpenAI を使う機能は API キーの用意とレート・コストに注意してください。API 呼び出しはリトライロジックがありますが、失敗時は安全側のフォールバック（例: 0.0）で継続します。
- Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（設計上の注意）。
- kill.flag（KILL_FLAG_PATH）を作成すると ExecutionEngine 停止を要求できます。KillSwitch はリスク基準に基づいて自動書き込みします。
- process priority や cpu affinity の設定を行うユーティリティがあります（psutil を利用）。パーミッションや OS により設定できない場合はログが出ます。

---

## 主要ファイル / ディレクトリ構成

リポジトリの主要な構成（src/kabusys 以下を抜粋）:

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を変更可。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBroker を使用。

- config.py
  - 環境変数の読み込み・Settings クラス。.env / .env.local の自動ロードロジックを含む。

- ai/
  - news_nlp.py            — ニュースの LLM センチメント評価（ai_scores への書き込み）
  - regime_detector.py     — ma200 + マクロニュースを合成した市場レジーム判定

- monitoring/
  - monitoring_db.py       — SQLite スキーマ初期化・監視用読み書きラッパー（MonitoringDB）
  - system_monitor.py      — CPU/メモリ/ディスク・PID・データ鮮度の監視
  - trade_monitor.py       — 注文滞留・約定異常の検出
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の書き込みロジック
  - alert_manager.py       — LINE 通知ラッパー
  - monitoring_engine.py   — 各モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (※長い実装ファイル群の一部)
  - order_record.py
  - execution_engine.py
  - broker_factory.py / broker_api.py
  （発注フロー・ブローカーインターフェース・リコンシリエーション等）

- research/
  - factor_research.py     — momentum / volatility / value のファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / summary など

- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 注文株数算出・上限・集約スケーリング
  - risk_adjustment.py     — セクターキャップ、レジーム乗数

- tools/
  - paper_verification_report.py — paper_trading DB からレポートを生成

- utils/
  - process_priority.py    — プロセス優先度・CPU affinity のユーティリティ

パッケージ初期化ファイル:
- __init__.py（kabusys パッケージのバージョン情報など）

---

## 例: よくある起動手順（簡易）

1. 仮想環境を作る・パッケージをインストール
2. .env に必要な値（OPENAI_API_KEY, KABU_API_PASSWORD, など）をセット
3. DuckDB / SQLite の初期データを準備（prices_daily 等はリサーチ機能で必須）
4. 監視を起動（推奨: デーモン or systemd で）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
5. Execution を起動
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
6. ダッシュボード / レポートで結果を確認
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 開発 / 貢献メモ

- テスト: 各モジュールは純粋関数部分（portfolio、research 等）を単体テストしやすい構造です。外部 API 呼び出し部分はモック可能な設計になっています（_call_openai_api 等は patch で差し替え可能）。
- マイグレーション: monitoring_db.init_monitoring_db は既存 DB に対して列追加マイグレーションを含みます（冪等）。
- ロギング: 標準 logging を使用。運用時は LOG_LEVEL 環境変数等で調整してください（Settings.log_level を参照）。

---

必要であれば README にサンプル .env.example や requirements.txt、systemd ユニットファイル、より詳細な運用手順（監視アラート設定、OpenAI の料金試算、DuckDB データロード方法など）も追記できます。どの情報を優先して追加しましょうか？