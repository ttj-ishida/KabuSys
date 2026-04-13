# KabuSys

日本株自動売買システムのコアライブラリ群と運用ユーティリティ群のリポジトリです。  
本リポジトリには、ExecutionEngine（発注実行）、Monitoring（監視・アラート）、Research（因子・特徴量解析）、AI 補助（ニュース NLP / レジーム判定）、ポートフォリオ構築ユーティリティなどが含まれます。

---

## プロジェクト概要

- 目的：日本株のアルゴリズム売買に必要なコンポーネント（発注、リスク管理、監視、研究、AI 補助）を集約したライブラリと運用スクリプトを提供します。
- 設計方針：
  - DuckDB / SQLite を用いたローカルデータ処理（prices_daily / raw_financials / raw_news 等）
  - Execution と Monitoring はファイルベースの DB（SQLite）でログ・状態を永続化
  - Paper Trading（モックブローカー）と Live（実ブローカー）を環境変数で切り替え
  - OpenAI API を使ったニュースセンチメント / レジーム判定機能（外部 API 呼び出しはオプション）
  - 冪等・フェイルセーフ設計（DB マイグレーション・部分書き込み保護・リトライ等）

---

## 主な機能一覧

- Execution（発注）
  - OrderManager / OrderRepository / ExecutionEngine による注文作成・送信・状態管理
  - Reconciler による再起動時の自動同期・ポジション照合
  - RiskManager による注文ごとのリスク制御（rate limit / circuit breaker 等）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス PID・データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager: LINE Push によるアラート送信
  - streamlit ベースの監視ダッシュボード

- Research（調査）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily, raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）や統計サマリ

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重 / スコア重み、リスク調整（セクター上限 / レジーム乗数）、ポジションサイズ決定（単元株丸め含む）

- AI（補助）
  - news_nlp: raw_news を集約し OpenAI による銘柄別センチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime を判定

- ユーティリティ
  - process_priority：Windows/Linux の差分を吸収してプロセス優先度 / CPU affinity を設定
  - 環境設定管理 Settings（.env 自動読み込み・検証）

---

## セットアップ手順

前提
- Python 3.9+（各自の環境に合わせてください）
- システムに DuckDB, SQLite の動作環境あり

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（サンプル）
   - pip install duckdb psutil requests streamlit openai

   ※プロジェクトに requirements.txt が無い場合、上記を基本セットとして必要に応じて追加してください。

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（既存 OS 環境変数を保護）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (paper_trading の場合: instant | partial | never | reject) — デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - PID_FILE_PATH / KILL_FLAG_PATH（監視 / 制御用）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

5. データディレクトリの作成
   - mkdir -p data

6. DB 自動初期化
   - run_monitoring / run_execution などの起動スクリプトは起動時に必要な監視テーブルを作成します（init_monitoring_db を実行）。

---

## 使い方（代表的なコマンド）

- ExecutionEngine（発注エンジン）を起動
  - 通常（KABUSYS_ENV=live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（モックブローカー、DB を data/paper_trading.db に分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  実行時、プロセス優先度を "high" に設定する処理が最初に走ります。

- Monitoring（ポーリングループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

  注意: Monitoring は KABUSYS_ENV に関わらず本番の SQLITE_PATH（SQLITE_PATH 環境変数で指定）を使用します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいは引数で DB を指定: --db path/to/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY か関数引数で指定）
  - プログラム内部から呼び出す:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - 両機能とも DB（DuckDB 接続）上の raw_news / news_symbols / ai_scores / market_regime を参照/更新します。

---

## 動作上の注意・運用メモ

- .env の自動読み込み
  - .env のパースはシェル風の構文（export KEY=...、引用符、インラインコメントの一部処理）をサポートします。
  - OS の既存環境変数は保護され、.env.local は .env より優先して上書きされます。

- Paper Trading と Monitoring の DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
  - run_monitoring は常に sqlite_path（監視 DB、デフォルト data/monitoring.db）を使用します。

- Kill Switch（停止フラグ）
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は起動時に kill flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START）を用意しています（Settings.kill_flag_clear_on_start）。

- プロセス優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼びます。権限によっては設定に失敗することがあり、その場合は警告ログが出ます。

- OpenAI API 呼び出し
  - レートリミットや一時的なネットワーク障害に対して指数バックオフでリトライしますが、API キー未設定の場合は例外になります（明示的にハンドルしてください）。
  - AI 出力のバリデーションを行ってから DB に書き込みます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — Settings / .env 読み込みロジック
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル定義と MonitoringDB ラッパ
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
    - (その他 broker / engine / repository 等のモジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに execution/broker_*、data パイプライン等のモジュールが含まれます。）

---

## 開発・拡張のヒント

- DuckDB を用いたファクター計算は SQL + Python の組合せで記述されており、prices_daily / raw_financials テーブルが揃えばローカルでの検証が可能です。
- AI 関係の API 呼び出し部分（_call_openai_api）はテスト用に patch / mock 可能な形で設計されています。
- MonitoringDB は冪等な初期化（init_monitoring_db）と簡易マイグレーション（カラム追加）を備えています。新しいカラムを追加する際は既存 DB への互換性を配慮してください。
- OrderManager / Reconciler はクラッシュ耐性を考慮した二相永続化やスキップロジックを実装しています。ブローカー API 実装を追加する際は BrokerAPIProtocol を満たすように実装してください。

---

もし README に追加したい実行例や .env のサンプル、または CI / テスト手順（ユニットテストの実行方法など）があれば教えてください。README をそれに合わせて拡張します。