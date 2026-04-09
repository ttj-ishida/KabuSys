# KabuSys

日本株向け自動売買フレームワーク（ライブラリ群）。ポートフォリオ構築、ポジションサイズ計算、監視、注文管理、LLM を使ったニュース／レジーム評価などの機能をモジュール化して提供します。

注意: 本リポジトリは取引ロジック・実行コンポーネントを含みます。実際の資金を動かす際は十分なテストと安全対策を行ってください。

---

## 概要

KabuSys は次のような責務を持つ Python パッケージです。

- ファクター計算・リサーチ（DuckDB 上の時系列データを参照）
- 銘柄選定・重み・ポジションサイズ計算（PortfolioConstruction に準拠した純粋関数群）
- リスク制御（セクター集中制限、レジーム乗数、Gate 検査等）
- ExecutionEngine / OrderManager による発注ワークフロー（ブローカー API 抽象化）
- リコンシリエーション（再起動後の自動同期）
- 監視機能（System/Trade/Risk モニタ、LINE 通知、kill flag）
- AI 統合（OpenAI を用いたニュースセンチメント評価、マクロセンチメント → レジーム判定）
- 監視ダッシュボード（Streamlit）

パッケージ名: `kabusys`  
バージョン: `0.1.0`（src/kabusys/__init__.py）

---

## 主な機能一覧

- portfolio
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights, calc_score_weights
  - ポジションサイズ計算: calc_position_sizes
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier

- research
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ

- ai
  - ニュースセンチメントスコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- execution
  - Broker API 抽象（protocol 型）
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine（セッション制御、push/drain、kill switch）

- monitoring
  - MonitoringDB（SQLite）、DB 初期化ユーティリティ
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - LINE 通知: AlertManager
  - Streamlit ダッシュボードスクリプト

- config
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - Settings オブジェクト経由で設定取得（例: settings.jquants_refresh_token）

---

## 必要条件 / 依存

最低限の依存ライブラリ（抜粋、実際は requirements.txt を参照してください）:

- Python 3.10+
- duckdb
- openai
- requests
- psutil
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）

インストール例（仮）:
pip install duckdb openai requests psutil streamlit

※ 実際のプロジェクトでは requirements.txt / poetry 等を用いて依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存のインストール
   - pip install -r requirements.txt
   - あるいは手動で: pip install duckdb openai requests psutil streamlit

3. 環境変数 (.env) の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置けます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API トークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
   - LINE_USER_ID — LINE 通知先ユーザ ID（任意）
   - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH — 監視DB（default: data/monitoring.db）
   - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH など（paper trading 用）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=yyyyyyyy
   OPENAI_API_KEY=sk-...

4. データディレクトリ準備
   - data/ ディレクトリを作成:
     mkdir -p data

5. 監視DB 初期化（SQLite 接続を渡して初期テーブル作成）
   - Python で:
     from sqlite3 import connect
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

---

## 使い方（代表例）

- 設定参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- DuckDB を使ったファクター計算（research）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))

- AI ニューススコアリング
  from kabusys.ai import score_news
  # conn: duckdb connection, target_date: datetime.date
  n = score_news(conn, target_date, api_key="sk-...")

- 市場レジーム判定（OpenAI を併用）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key=None)  # 環境変数 OPENAI_API_KEY が使用される

- 監視ダッシュボード（Streamlit）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringDB / MonitoringEngine の利用
  - init_monitoring_db() によりテーブルを作成してから、MonitoringEngine を構成して run/run_once を呼びます。
  - AlertManager を作成して LINE 通知を有効にできます。

- ExecutionEngine（実稼働用）
  - ExecutionEngine は BrokerAPIProtocol 実装（kabu station client 等）、OrderRepository、RiskManager、OrderManager、DuckDB 接続などの具体実装が必要です。
  - 実行: engine.run_session()
  - ※ 本エンジンはファイルベースの kill.flag / pid ファイル管理やリコンシリエーションを行います。実行前に設定と検証を十分に行ってください。

---

## 主要モジュール・ディレクトリ構成

（src/kabusys 以下の主要ファイル／モジュール）

- kabusys/
  - __init__.py                      — パッケージ定義（__version__ 等）
  - config.py                        — 環境変数読み込みと Settings
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定 / 重み計算
    - position_sizing.py             — 株数計算・aggregate cap
    - risk_adjustment.py             — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — momentum/volatility/value 等
    - feature_exploration.py         — forward returns, IC, summary
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースを OpenAI でスコア（ai_scores 書込）
    - regime_detector.py             — ETF MA + LLM によるレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py               — MonitoringDB クラス / DB 初期化
    - system_monitor.py              — CPU/メモリ/データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - alert_manager.py               — LINE 通知ラッパ
    - kill_switch.py                 — kill.flag 管理
    - monitoring_engine.py           — 各モニタを束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - broker_api.py                  — Broker API 型・データモデル・例外
    - order_manager.py               — 注文状態管理（OrderManager）
    - reconciler.py                  — 自動リコンシリエーション
    - execution_engine.py            — 実行エンジン（signal/drain loop）
    - ...（OrderRepository や order_record 等は別ファイルに存在）
  - monitoring/、research/、portfolio/、ai/ の各 __init__ は公共 API をエクスポート

---

## 設計上の注意点・運用上の注意

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から探索します。配布後の実行環境では挙動に注意してください。
- AI 絡みの処理（news_nlp, regime_detector）は OpenAI API を呼ぶため、API 失敗時はフォールバック（多くは 0.0）して継続する設計です。ただし品質は保証されないため運用前に検証してください。
- ExecutionEngine / OrderManager はブローカー実装（BrokerAPIProtocol）を別途用意する必要があります。実稼働前にローカルで paper trading モード等で十分に検証してください。
- kill.flag / PID ファイルを用いてプロセス管理を行います。CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD などの設定を活用してください。
- DuckDB / SQLite のスキーマ期待値（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）を満たすデータが必要です。

---

## 開発 / テスト

- モジュールはなるべく純粋関数（DB 参照範囲が明示されたもの）とし、テストしやすい設計になっています。ユニットテストの追加を推奨します。
- AI 呼び出し関数はテスト時に差し替え（モック）可能なように実装されています（例: news_nlp._call_openai_api の patch）。

---

## ライセンス / 責任

本プロジェクトは取引や資金を伴う運用に関わるため、使用者側の責任において利用してください。本 README はコードの要約であり、法的保証を与えるものではありません。実運用する際は必ず適切な検証と監査を行ってください。

---

必要があれば、以下の情報を追加で生成します:
- requirements.txt（推奨バージョン付き）
- .env.example のテンプレート
- よくある実行例（ExecutionEngine の組み立てサンプル）
ご希望があれば教えてください。