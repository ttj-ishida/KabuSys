# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ。ポートフォリオ構築、ポジションサイジング、リスク調整、ファクター計算、ニュースNLP（OpenAI）によるセンチメント評価、監視（Monitoring）等のユーティリティ群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的とした Python モジュール群です。

- DuckDB に保存された株価・財務データを用いたファクター計算・リサーチ機能
- シグナル → 発注処理（ExecutionEngine）や Order 管理（OrderManager / Reconciler）
- セクター集中制限やレジーム依存の資金乗数、株数計算などのポートフォリオ構築ロジック
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価・市場レジーム検出
- SQLite を用いた監視ログ永続化・監視エンジン、Streamlit ダッシュボード、LINE 通知連携

設計方針として多くのモジュールは純粋関数（副作用なし）または DB 接続のみを受け取り外部副作用を最小化するように実装されています。安全性（フェイルセーフ、リトライ、冪等性）に配慮した実装が特徴です。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）
- ポートフォリオ構築
  - シグナル選定（select_candidates）
  - 等重み・スコア重みの重み付け（calc_equal_weights / calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Z スコア正規化ユーティリティ（kabusys.data.stats と連携）
- AI（OpenAI）
  - ニュースを銘柄ごとに集約して LLM でセンチメント評価（score_news）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（score_regime）
  - API 呼び出しに対するリトライ・バリデーション・スコアクリップ
- 実行・発注系
  - Broker API 抽象（Protocol / データモデル / 例外）
  - OrderManager（作成・送信・同期・キャンセル）、Reconciler（起動時リコンシリエーション）
  - ExecutionEngine（シグナル処理 + WebSocket プッシュドレイン）
- 監視（Monitoring）
  - MonitoringDB（SQLite スキーマ・CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 通知）
  - Streamlit ダッシュボード（監視 UI）

---

## 必要条件（例）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
- その他、プロジェクトに応じた依存がある可能性があります（pyproject.toml を確認してください）。

---

## セットアップ手順

1. リポジトリを取得（例）
   - git clone ... またはプロジェクトディレクトリを配置

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai requests psutil streamlit

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください:
   pip install -r requirements.txt または pip install -e .）

4. 環境変数 / .env ファイルを用意
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 主要な環境変数（一部）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信しません）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE（デフォルト "instant"、有効値: instant|partial|never|reject）
   - KABUSYS_ENV（development|paper_trading|live）
   - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値（CPU/MEM/DISK）

   設定の取得は `from kabusys.config import settings` を使います（例: settings.jquants_refresh_token）。

---

## 使い方（代表的な例）

- 設定値の参照
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

- DuckDB を使ったファクター計算（例: モメンタム）
  - import duckdb
    from datetime import date
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    result = calc_momentum(conn, date(2026, 3, 20))
    # result は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...] のリスト

- 将来リターン / IC の計算
  - from kabusys.research import calc_forward_returns, calc_ic
  - fwd = calc_forward_returns(conn, date(2026,3,20))
  - factors = calc_momentum(conn, date(2026,3,20))
  - ic = calc_ic(factors, fwd, "mom_1m", "fwd_1d")

- ニュースセンチメントスコアの作成（OpenAI 必須）
  - from kabusys.ai import score_news
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026,3,20), api_key="sk-...")
    # ai_scores テーブルへ書き込み。戻り値は書き込んだ銘柄数

- 市場レジーム判定（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,3,20), api_key="sk-...")

- 監視 DB 初期化
  - import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine 等（本番的な組み立て）
  - ExecutionEngine の利用には BrokerAPI の実装、OrderRepository（SQLite）、RiskManager、OrderManager、Reconciler などの具体実装が必要です。これらを組み合わせて EngineConfig を渡し、engine.run_session() を呼ぶ形になります。実運用では PID ファイル / kill.flag / kill_switch の流れやリコンシリエーションに注意してください。

---

## 自動 .env 読み込みの挙動

- 読み込み優先順位（高 → 低）:
  1. OS 環境変数
  2. .env.local（存在すれば .env の値を上書き）
  3. .env
- プロジェクトルートの検出基準: .git ディレクトリまたは pyproject.toml の存在場所を起点に探索します（__file__ を基準にするため CWD に依存しません）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースは export KEY=val, quoted values, inline comments 等に対応しています。

---

## ディレクトリ構成（主要部分）

（src/kabusys 配下の主なモジュール）

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI）
    - regime_detector.py  — 市場レジーム判定（OpenAI + ETF MA）
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py   — 株数計算・資金配分ロジック
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ・CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - order_manager.py
    - order_repository.py (参照あり)
    - reconciler.py
    - execution_engine.py
    - ...（OrderRecord, RiskManager 等）
  - portfolio/, research/, monitoring/, ai/ のテストやユーティリティが含まれます（プロジェクト全体の詳細はソースを参照してください）。

---

## 開発・運用上の注意

- OpenAI を利用する処理（news_nlp / regime_detector）は API 呼び出しを伴い、キーが必要です。失敗時はフォールバック（0.0 等）して継続する設計ですが、API 利用制限に注意してください。
- ExecutionEngine は外部 Broker 実装（BrokerAPIProtocol）を前提にしており、単体では動きません。実ブローカーとの接続実装に十分なテスト・安全対策（シミュレーション、paper_trading モード）を行ってください。
- kill.flag、PID ファイルなどによるプロセス制御や冪等性設計（DELETE→INSERT を避ける等）に配慮した実装が複数箇所にあります。運用時は該当ファイルの扱いに注意してください。
- DuckDB / SQLite のスキーマやテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime / monitoring テーブル等）は想定された形式でデータを投入する必要があります。

---

必要であれば、以下を追加で作成できます:
- インストール用の pyproject.toml / requirements.txt の例
- 簡易的な broker モック実装例（テスト用）
- 各モジュールの API 使用例を含むユーザ向けチュートリアル

どの追加を希望するか教えてください。