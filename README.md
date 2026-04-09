KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視ユーティリティ群です。本リポジトリは以下の責務を持つモジュール群で構成されています。

- ポートフォリオ構築（候補選定・配分・株数決定・セクターキャップ）
- ファクター計算・特徴量解析（DuckDB 上の時系列データを利用）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- 発注エンジン（Order 管理・再同期・kill switch を含む）
- 監視・アラート（LINE プッシュ、SQLite によるログ永続化、Streamlit ダッシュボード）
- 設定管理（.env 自動読み込み・環境変数経由）

特徴（機能一覧）
----------------
- 環境変数 / .env 自動ロード（プロジェクトルートの検出に基づく）
- ポートフォリオ構築ロジック（等配分・スコア加重・リスクベースの単元丸め）
- セクター集中制限（既存ポジション比率に基づく候補フィルタリング）
- レジームに応じた投下資金の乗数（bull/neutral/bear）
- ファクター計算（Momentum, Volatility, Value 等） — DuckDB クエリベース
- ファクター有効性解析（forward returns, IC, 統計サマリー）
- AI ニューススコアリング（OpenAI gpt-4o-mini を使用、結果を DuckDB の ai_scores に書込）
- 市場レジーム判定（ETF MA200 と LLM マクロセンチメントの合成）
- 実行エンジン（Signal → 注文、WebSocket push drain、Reconciler による再同期）
- 監視スタック（MonitoringDB: SQLite、RiskMonitor、SystemMonitor、TradeMonitor、AlertManager（LINE））
- Streamlit ベースの監視ダッシュボード

セットアップ
----------
前提
- Python 3.10+（PEP 604 の型記法（X | Y）を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）、requests、psutil、streamlit など

例: pipenv / venv を使った最小インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

2. 必要パッケージをインストール（実際の requirements.txt がないため代表的なものを列挙）
   - pip install duckdb openai requests psutil streamlit

（プロダクション用途では lock ファイルや requirements.txt を用意してください）

環境変数（主な設定）
-------------------
KabuSys は環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動ロードは .env（優先度低）→ .env.local（優先度高）で、OS 環境変数は上書きされません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai/news/regime モジュールで利用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Messaging API トークン（監視アラート）
- LINE_USER_ID: LINE ユーザ ID（監視アラートの送信先）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行制御関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env / .env.local のパース仕様（簡単な注意）
- export KEY=val 形式に対応
- 値にシングル/ダブルクォートがある場合はエスケープも処理
- コメントは # の直前に空白がある場合のみ inline コメント扱い
- .env.local は .env の上書き（override=True）だが OS 環境変数は保護される

使い方（代表的な操作例）
-----------------------

1) Monitoring DB の初期化（SQLite）
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

2) Streamlit ダッシュボード起動
コマンド例:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
（起動時引数 --db で監視 DB を指定可能）

3) News NLP（OpenAI を用いたニューススコア付与）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date はスコア化する「日付」を指定（例: 2026-03-20）
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```
- api_key を省略した場合は環境変数 OPENAI_API_KEY を参照します。
- 処理はフェイルセーフ設計（API 失敗時は該当チャンクをスキップ）。

4) Market Regime 判定（ETF 1321 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```
- DB に market_regime レコードを冪等に書き込む（DELETE→INSERT）。

5) ExecutionEngine（要組み立て）
ExecutionEngine は BrokerAPIProtocol 実装・OrderRepository・RiskManager・OrderManager 等の依存を注入して利用します。テストや小規模実行では ExecutionEngine.run_session() を呼ぶことでセッション（シグナル処理→push drain）を実行できます。起動時に PID 書き込み / kill.flag チェックが行われます。

（注）実際の broker 実装や OrdersDB スキーマ、RiskManager 等は本 README の対象外です。リポジトリに含まれる execution/ モジュールを参照してください。

API / ライブラリ参照（主要関数）
--------------------------------
- kabusys.config.settings — 環境設定アクセサ
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes
- kabusys.portfolio.apply_sector_cap / calc_regime_multiplier
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.ai.score_news（ニュース NLP） / kabusys.ai.score_regime（regime_detector）
- kabusys.monitoring.init_monitoring_db / MonitoringDB / MonitoringEngine / AlertManager / KillSwitch
- kabusys.execution.ExecutionEngine / OrderManager / Reconciler（発注・再同期関連）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数/.env ロード & Settings
- portfolio/
  - __init__.py
  - portfolio_builder.py          — 候補選定・重み計算
  - risk_adjustment.py            — セクター制限・レジーム乗数
  - position_sizing.py            — 発注株数計算・集約キャップ
- research/
  - __init__.py
  - factor_research.py            — Momentum / Volatility / Value 等
  - feature_exploration.py        — forward returns, IC, summary
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースを LLM に送って ai_scores に書込
  - regime_detector.py            — ETF MA + マクロ LLM で市場レジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py              — SQLite テーブル作成・MonitoringDB
  - system_monitor.py             — システム状態・データ鮮度監視
  - trade_monitor.py              — 注文滞留・約定異常監視
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - kill_switch.py                — kill.flag 制御
  - alert_manager.py              — LINE Push 通知
  - monitoring_engine.py          — 監視ループ束ね
  - streamlit_dashboard.py        — Streamlit ダッシュボード
- execution/
  - broker_api.py                 — Broker API のデータモデル / Protocol / 例外
  - order_manager.py              — OrderState マシンの外向け API
  - reconciler.py                 — 再同期 / ポジション差分検出
  - execution_engine.py           — Signal Pull / Push Drain のエンジン
  - （他: order_repository, order_record, risk_manager 等が想定）
- ai/（上記）
- research/（上記）
- portfolio/（上記）

注意事項 / 運用上のヒント
------------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml の所在）を基に行います。テストで自動ロードを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 経由の処理は API レート制限・一時エラーに対してリトライ実装を持ちますが、API キー管理・コストには注意してください。
- kill.flag の存在は ExecutionEngine の起動を防ぎます（KILL_FLAG_CLEAR_ON_START=1 で起動時に自動クリアする設定あり）。
- データ参照は DuckDB 上の prices_daily / raw_financials / raw_news 等を前提としています。データのスキーマやロード処理（data.pipeline 等）は別モジュールに実装される想定です。

貢献 / テスト
---------------
- コードはモジュールごとに純粋関数または DB 層・API 層を分離する設計です。ユニットテストでは外部 API 呼び出し（OpenAI / Broker）をモックすることを推奨します。
- 自動ロードされた環境変数がテストに影響する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な env を明示的に注入してください。

ライセンス / その他
-------------------
（ライセンス情報がプロジェクト内にある場合はここに記載してください）

最後に
------
この README はコードベースの主要機能をまとめたガイドです。詳細な実行例・依存管理・CI 設定等はプロジェクト固有の運用ドキュメントや contrib ガイドを別途用意してください。質問や補足があれば教えてください。