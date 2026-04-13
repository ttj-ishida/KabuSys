# KabuSys

KabuSys は日本株の自動売買・研究プラットフォームです。価格データと財務データを用いたファクタ計算、ポートフォリオ構築、発注実行、監視（Monitoring）、およびニュースに基づく AI 評価などの機能を備えています。

---

## 概要

本リポジトリは以下の主要コンポーネントで構成されています。

- Execution（発注エンジン）: ブローカークライアントを通じた注文生成・送信・状態管理、リコンシリエーション機能
- Monitoring（監視）: システム・注文・リスク監視、アラート送信、kill flag によるエンジン停止
- Portfolio（ポートフォリオ構築）: 候補選定・重み付け・株数計算・セクター制約
- Research（研究）: ファクター計算（Momentum / Volatility / Value）や特徴量解析ツール
- AI（ニュース NLP / レジーム検出）: OpenAI を用いたニュースセンチメント評価や市場レジーム判定
- Tools: Paper Trading 検証レポートなどのユーティリティスクリプト
- utils: プロセス優先度 / CPU affinity 設定など

設計方針として、データ処理（DuckDB）と運用ログ（SQLite）を分離し、テスト可能でフェイルセーフな動作を目指しています。

---

## 主な機能一覧

- モニタリング
  - CPU / メモリ / ディスク / 実行プロセス監視
  - 注文滞留・約定異常価格検出
  - ドローダウン / ポジション数上限の監視（kill.flag による停止）
  - LINE へのプッシュ通知（AlertManager、クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- 発注エンジン（ExecutionEngine）
  - ブローカー抽象化（実口座 / Paper Trading の切替）
  - リスク管理（最大ポジション比率 / 利用率 / レート制限等）
  - リコンシリエーション（再起動後の自動同期）
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等配分 / スコア加重 / リスクベース配分
  - セクターキャップ、レジーム乗数
  - 単元株丸め・集約キャップ処理
- 研究・分析
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）や統計要約
- AI（OpenAI）
  - ニュースを銘柄単位に集約しセンチメント（-1〜1）を取得して ai_scores に格納
  - マクロ記事 + ETF MA200 を使った市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成（期間指定可）

---

## セットアップ手順

前提
- Python 3.10+
- OS: Linux / macOS / Windows（psutil による制約あり）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - （その他：logging 等は標準ライブラリ）

推奨手順（例）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt がある場合はそれを利用）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - .env または環境変数で設定（自動ロードはプロジェクトルートの `.env` / `.env.local` を探索）
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - SQLITE_PATH（monitoring 用 DB, デフォルト: data/monitoring.db）
     - DUCKDB_PATH（時系列データ格納 DuckDB, デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔, デフォルト 60）
   - 自動ローディングを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

データ準備
- DuckDB（prices_daily / raw_financials / raw_news などのテーブル）はリサーチ・AI 機能で参照されます。実データを用いる場合は DuckDB ファイルに事前にテーブルを作成・ロードしてください。
- monitoring 用 SQLite（data/monitoring.db）は run_monitoring.py 実行時に必要テーブルが冪等に作成されます。

---

## 使い方（主なコマンド）

モジュールはパッケージとして実行できます（例: python -m kabusys.<module>）。

1. ExecutionEngine を起動
   - 本番環境
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - Paper Trading（MockBroker を使用、DB は data/paper_trading.db）
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 動作の流れ: 起動時に PID ファイルを書き込み、ブローカー接続 → Reconciler → セッション実行

2. Monitoring（ポーリングループ）を起動
   - MONITOR_POLL_INTERVAL 秒でポーリング（デフォルト 60 秒）
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - 監視は常に production 用 sqlite_path を使います（Settings による切替なし）

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ローカルの monitoring.sqlite を read-only で開いてダッシュボードを表示します

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスを明示する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI / レジーム判定をスクリプトから呼び出す（例）
   - Python から直接呼ぶ:
     - from datetime import date
       import duckdb
       from kabusys.ai.news_nlp import score_news
       conn = duckdb.connect("data/kabusys.duckdb")
       score_news(conn, date(2026,4,1), api_key="sk-...")
   - OpenAI API キーは `OPENAI_API_KEY` 環境変数でも渡せます。

注意事項
- `KABUSYS_ENV=paper_trading` は MockBrokerClient を使い、紙トレ用 DB（PAPER_TRADING_SQLITE_PATH）にのみ記録します。本番 DB とデータは完全分離されます。
- run_monitoring は KABUSYS_ENV に関わらず production 用 sqlite_path（Settings.sqlite_path）を使用します（監視ログの一元化）。

---

## 設定（Settings）について

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。

主なプロパティ（Defaults を含む）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: data/monitoring.db
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定モード）

必須環境変数は Settings が起動時にチェックし、未設定なら ValueError を発生させます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（MA200 + マクロ NLP）
    - monitoring/
      - monitoring_db.py       — SQLite テーブル作成 & 永続化 API
      - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
      - trade_monitor.py       — 注文滞留 / 約定異常監視
      - risk_monitor.py        — ドローダウン / ポジション数監視
      - kill_switch.py         — kill.flag 書き込みロジック
      - alert_manager.py       — LINE push 通知
      - monitoring_engine.py   — 各 Monitor 統合ポーリング
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ...                    — ブローカー抽象化等
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
      - process_priority.py    — プロセス優先度 / CPU affinity

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用・注意点

- PID ファイル: ExecutionEngine は起動時に PID ファイルを作成します。SystemMonitor はこれを見てプロセス生存確認を行い、stale PID を発見した場合は削除してリスクログを記録します。
- kill.flag: KillSwitch はデータベース上のリスク条件（大きなドローダウン等）が成立した場合にファイルを書き込み、ExecutionEngine 側でこのフラグを検知して安全に停止する運用を想定しています。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する軽微なマイグレーション（カラム追加）も行います。
- テスト可能性: 多くの API は外部呼び出し（OpenAI / ブローカー / HTTP）を抽象化しており、ユニットテストでモックしやすい設計になっています。

---

## よくあるコマンドまとめ（例）

- 仮想環境作成・依存インストール
  - python -m venv .venv; source .venv/bin/activate; pip install -r requirements.txt
- Execution 起動（paper trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 30s）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README はここまでです。ローカルでの初期セットアップや DuckDB に関する具体的なデータロード方法、ブローカー接続まわりの実装 (kabu API の設定等) は別途ドキュメント（.env.example / データ準備手順）を参照してください。必要があれば運用手順書やデプロイ手順のテンプレートを追加で作成します。