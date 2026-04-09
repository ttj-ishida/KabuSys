# KabuSys

KabuSys は日本株自動売買システム向けの内部ライブラリ群です。  
ポートフォリオ構築、リスク調整、ポジションサイズ計算、ファクター・リサーチ、AI（ニュースセンチメント／レジーム判定）、発注エンジン・再同期、監視（Monitoring）など、実運用を想定したコンポーネント群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは、アルゴリズムトレーディングのためのモジュール群を提供します。主な設計方針：

- 各機能は可能な限り純粋関数・副作用を限定して実装（DBアクセス・外部API呼出し箇所は明示）。
- DuckDB / SQLite をデータ格納に利用（分析用・監視用の永続化）。
- OpenAI を用いたニュースのセンチメント計算やマクロ判定もサポート（フェイルセーフ実装）。
- 本番運用を想定した監視・kill switch・PID 管理などを含む。

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出、.env → .env.local の順で読み込み）
  - 必須環境変数チェック（Settings クラス）
- ポートフォリオ構築（kabusys.portfolio）
  - シグナルの候補選定（select_candidates）
  - 等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - セクター集中制限の適用（apply_sector_cap）
  - レジーム乗数計算（calc_regime_multiplier）
  - 株数決定（calc_position_sizes）：リスクベース／等分配／スコア加重、lot 単位丸め、コストバッファ、aggregate cap
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続を受ける）
  - 将来リターン計算、IC（スピアマン）計算、要約統計量
- AI（kabusys.ai）
  - ニュースの NLP センチメント（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を使う設計（リトライ、レスポンス検証、スコアクリップ等を実装）
- 発注・実行（kabusys.execution）
  - Broker API のプロトコル定義（broker_api）
  - Order 管理（OrderManager、OrderRepository と組合せ）
  - ExecutionEngine：Signal Pull + WebSocket Push のハイブリッド実行ループ、kill switch 統合、再同期（Reconciler）
  - Reconciler：起動時の注文・ポジション再照合
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）層とスキーマ初期化（init_monitoring_db）
  - System / Trade / Risk Monitor、AlertManager（LINE Push）、
  - KillSwitch（flag ファイルによる外部停止シグナル）
  - Streamlit ベースの監視ダッシュボード（簡易 UI）

---

## 必要環境（推奨）

- Python 3.10+
- 主要依存（代表例）:
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit
- 実運用では kabuステーション等のブローカークライアント実装が必要

インストール例（venv を想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil requests streamlit
# 開発時にパッケージとしてインストールする場合
pip install -e .
```

（このリポジトリに requirements.txt がない場合は上記のように個別インストールしてください）

---

## 環境変数（主要なキー）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイルの保存先（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — 実行モード（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動読み込み:
- プロジェクトルート（.git または pyproject.toml が見つかるディレクトリ）から .env を読み、続けて .env.local を上書き読み込みします。
- OS の環境変数は保護され、.env（override=False）では上書きされません。.env.local は override=True で OS 環境変数を上書きしません（protected キーは保護）。
- 自動読み込みを止める: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. DuckDB / SQLite DB ファイルを配置（なければアプリ側で自動作成される処理もあるが、監視DBスキーマは init_monitoring_db で初期化）
4. .env（または環境変数）を用意
   - .env.example を参考に必須キーを設定してください（このリポジトリに .env.example があれば参照）
5. 監視 DB の初期化（監視用 SQLite）:
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```

---

## 使い方（代表的な呼び出し例）

- 設定取得:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

- ポートフォリオ関数（候補選定・重み・ポジションサイズ）:
```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
sizes = calc_position_sizes(
    weights=weights,
    candidates=candidates,
    portfolio_value=10_000_000,
    available_cash=7_000_000,
    current_positions={},
    open_prices={'1234': 1200.0},
)
```

- リサーチ（DuckDB 接続を渡して利用）:
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- AI ニューススコアリング:
```python
from kabusys.ai import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監視ダッシュボード（Streamlit）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- MonitoringDB 初期化 & 使用（Python）:
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
db = MonitoringDB(conn)
db.log_system_status(cpu_percent=10.0, memory_percent=20.0, disk_percent=30.0, process_ok=True)
```

- ExecutionEngine 等は複数コンポーネント（Broker 実装、OrderRepository、RiskManager 等）を注入して使用します。実運用ではブローカークライアントの具象実装が必要です。主要クラス:
  - ExecutionEngine, OrderManager, Reconciler, MonitoringEngine, RiskMonitor など。

---

## 主要な注意点 / 補足

- OpenAI 利用
  - AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY を参照します。API 呼び出しは課金対象となるため注意してください。
  - レスポンスのバリデーションやリトライを備えていますが、API の停止時はフォールバック（スコア 0.0）で継続する設計です。
- 自動読み込み
  - config モジュールは import 時にプロジェクトルートを探索して .env/.env.local を自動読み込みします。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データのルックアヘッドに注意
  - ファクター計算・レジーム判定等は「ルックアヘッドバイアス」を避けるよう設計されています（target_date 未満のデータのみ使用等）。
- kill.flag / PID
  - ExecutionEngine は PID ファイルを書き、kill.flag による外部停止をサポートします。起動時の挙動は Settings.kill_flag_clear_on_start により制御可能です。
- DB スキーマ
  - MonitoringDB は upsert/マイグレーション処理を含みます。ai_scores、market_regime 等のテーブルは AI モジュールの出力先として期待されます（DuckDB schema は利用箇所の SQL を参照）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
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
    - execution_engine.py
    - reconciler.py
    - (その他: order_repository, order_record, risk_manager 等は別ファイルとして想定)
  - ai、research、portfolio、monitoring、execution のテストや追加モジュールはプロジェクト拡張により配置

（ファイル単位のコメントや docstring に実装の設計意図が詳細に書かれています。具体的な実装参照を推奨します）

---

## 開発・拡張のヒント

- DuckDB を使った解析関数群は接続（DuckDBPyConnection）を受け取り SQL を直接走らせる形式です。データ準備（prices_daily / raw_financials / raw_news 等のテーブル）を整備してから関数を呼んでください。
- BrokerAPIProtocol を実装する具象クライアントを用意すれば、OrderManager / ExecutionEngine がそのまま利用できます。
- AI 周りはレスポンス検証や部分的な失敗時の保護（部分成功書き込み）を重視しています。OpenAI の呼び出し部分はモックしやすくテスト可能です（内部の _call_openai_api を patch する設計）。

---

もし README に追加してほしい具体的な情報（例: 実行のワークフロー図、サンプル .env.example、CI 設定、詳細な API 仕様書など）があれば教えてください。必要に応じて追記します。