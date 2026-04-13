# KabuSys

日本株自動売買システムのコンポーネント集（ライブラリ / 実行スクリプト / モニタリング / 解析ツール）。  
このリポジトリは取引実行エンジン、監視基盤、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI を用いたニュース NLP 等のモジュール群で構成されています。

## プロジェクト概要
- 目的: 日本株の自動売買を安全に運用するための実行エンジン、監視、リスク制御、検証ツール、研究用ユーティリティを提供します。
- 設計方針:
  - 本番と Paper Trading を明確に分離（環境変数 `KABUSYS_ENV`）。
  - DB は SQLite（監視ログ等）と DuckDB（価格・ファクター計算）を利用。
  - AI（OpenAI）によるニュースセンチメント / レジーム判定をオプションで統合。
  - フェイルセーフ（API失敗時の安全なフォールバック・ログ）を重視。

## 主な機能一覧
- Execution（発注）
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - BrokerClientFactory による実行時のブローカークライアント切替（paper_trading では Mock）
  - OrderManager / OrderRepository / Reconciler による状態管理と起動時リコンシリエーション
  - RiskManager による発注リスク制御

- Monitoring（監視）
  - SystemMonitor: プロセス生存・CPU/メモリ/Disk・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - KillSwitch: 条件で ExecutionEngine 停止フラグ（data/kill.flag）を作成
  - AlertManager: LINE Push による通知
  - MonitoringEngine: 上記をまとめてポーリング（run_monitoring.py）

- Portfolio（ポートフォリオ構築）
  - 銘柄選定・重み計算・単元丸めなど（等金額・スコア加重・リスクベース等）
  - セクターキャップ・レジーム乗数適用

- Research / Data
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- AI
  - news_nlp: OpenAI を用いたニュースごとの銘柄センチメント算出（ai_scores へ書き込み）
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 判定を合成して日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ベースの監視ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを使用してください）

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. 環境変数の設定
   - 必須（実行時に ValueError を出す項目）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 関連（AI機能を使う場合）:
     - OPENAI_API_KEY
   - その他（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH — 監視 DB（default: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE 等
   - .env の自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例 .env（最小）:
    JQUANTS_REFRESH_TOKEN=...
    KABU_API_PASSWORD=...
    OPENAI_API_KEY=...
    KABUSYS_ENV=paper_trading

## 使い方 / 実行例
- 実行エンジンを起動（デフォルト: KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - Paper Trading 環境で起動したい場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時は process priority を "high" に設定し、PID ファイルへ書き込み（Settings.pid_file_path）します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える: 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き（デフォルト: 60）
  - 監視は monitoring DB（Settings.sqlite_path）を使用。monitoring は環境にかかわらず本番 sqlite_path を使います（意図的な分離）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニューススコア、レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

## 環境変数・設定の主要まとめ（Settings によるデフォルト）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: AI 機能のために必要（任意機能）
- SQLITE_PATH: data/monitoring.db
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の Mock の振る舞い）
- LOG_LEVEL: DEBUG|INFO|...（default: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用）

注意:
- run_execution は Paper Trading の場合、`paper_sqlite_path` を使用して本番 DB と分離して動作します。
- run_monitoring は常に本番 sqlite_path を参照します（監視は本番 DB を基準に行うため）。

## ディレクトリ構成（主なファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings 定義
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化レイヤ
    - system_monitor.py      — CPU / メモリ / データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
    - __init__.py

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py    (その他 Execution 関連ファイルが存在する想定)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - (など)

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - process_priority.py
    - __init__.py

※ 上記は本リポジトリ内の主なファイルを抜粋した一覧です。実装の全体像はソースツリーを参照してください。

## 運用上のポイント
- PID / Kill Flag:
  - ExecutionEngine は起動時に PID を書き、SystemMonitor はそれを参照してプロセス生存を確認します。
  - KillSwitch はリスク条件で data/kill.flag を書き、Execution 停止を促します。起動時にフラグをクリアするオプションがあります（Settings.kill_flag_clear_on_start）。

- DB マイグレーション（軽微な自動対応）
  - init_monitoring_db は冪等でテーブルを作成し、既存テーブルにカラムがない場合は簡易マイグレーション（ALTER TABLE ADD COLUMN）を行います。

- フェイルセーフ:
  - AI API や外部 API の失敗時は安全側のデフォルト（例: macro_sentiment=0.0）で継続する設計です。
  - 監視系は例外を捕捉して継続するようになっています。

## 開発 / 貢献
- 新しい機能追加やバグ修正の際は:
  - 単体テストを追加（本コードベースの多くの関数は純粋関数でテストが容易）
  - DuckDB / SQLite のクリーンな接続管理を心がける
  - AI 関連は API コールを抽象化し、テスト時はモックで差し替え可能な設計を維持する

---

README に不足している点や、特定モジュールの詳細なドキュメント（API 仕様、設定例、運用手順）を希望される場合は、どの部分を深掘りするか教えてください。必要に応じて起動フロー図や環境変数一覧のテンプレートも作成します。