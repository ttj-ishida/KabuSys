# KabuSys

日本株向け自動売買 / リサーチ基盤ライブラリ (モジュール群のみ)。  
このリポジトリは、ポートフォリオ構築、ポジションサイズ計算、ファクター計算、ニュースNLP（OpenAI）を使ったセンチメント評価、実行エンジン／モニタリング等の主要ロジックを純粋関数／小粒モジュールとして提供します。

---

## 主な特徴（機能一覧）

- 環境設定読み込み
  - .env / .env.local を自動読み込み（OS 環境変数が優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定: スコア順ソート（select_candidates）
  - 重み算出: 等配分 / スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算: risk_based / equal / score（calc_position_sizes）
  - セクター上限適用 / レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- ニュース NLP（kabusys.ai）
  - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコアリング（score_news）
  - マクロニュース + ETF MA を用いた市場レジーム判定と DB 書き込み（score_regime）

- 実行系（kabusys.execution）
  - OrderManager / ExecutionEngine / Reconciler 等、ブローカー API 連携と注文状態管理
  - Broker API 抽象プロトコル、例外モデル

- 監視（kabusys.monitoring）
  - SQLite ベースの監視ログ層（MonitoringDB）
  - System / Trade / Risk モニタ、KillSwitch、LINE 通知（AlertManager）
  - Streamlit ダッシュボード（監視データ可視化）

---

## 前提・依存関係

主に次の Python パッケージが必要です（抜粋）:

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- requests
- psutil
- streamlit (ダッシュボード用)

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## 環境変数（主なもの）

.env / .env.local、もしくは OS 環境変数で設定します。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

主な変数例:

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須な箇所あり）
- KABU_API_PASSWORD: kabu ステーション / ブローカー API パスワード
- KABU_API_BASE_URL: kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH: ペーパートレード用設定
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行制御・監視関連
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

サンプル .env:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで使用）。
- .env.local は .env を上書きするため、ローカル秘密情報は .env.local に置くことを想定しています。

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに .env を作成（.env.example を参考）
5. DuckDB / SQLite データベースを準備（スキーマ用 SQL がある場合は実行）

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
# .env を作成
```

監視 DB の初期化（SQLite）:

```python
import sqlite3
from kabusys.monitoring import init_monitoring_db
conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```

---

## 使い方（主要ユースケース）

以下は典型的なモジュール呼び出し例です。各関数はモジュールドキュメント（docstring）に詳細があります。

- ポートフォリオ構築（メモリ内計算）

```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
sizes = calc_position_sizes(
    weights=weights,
    candidates=candidates,
    portfolio_value=10_000_000,
    available_cash=1_000_000,
    current_positions={},
    open_prices=open_prices,
)
```

- リサーチ（DuckDB 接続が必要）

```python
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
results = calc_momentum(conn, target_date)
```

- ニュース NLP（OpenAI 使用）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"Wrote scores for {written} symbols")
```

- レジーム判定（市場レジームを DB に書き込む）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

- 監視ダッシュボード（Streamlit）

起動:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- 監視 DB API（プログラムから）

```python
import sqlite3
from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
db = MonitoringDB(conn)
db.log_system_status(10.0, 20.0, 30.0, True)
```

- ExecutionEngine / OrderManager 等は依存オブジェクト（BrokerAPIProtocol 実装、OrderRepository、RiskManager 等）を組み合わせて使用します。これらはプロダクション環境に合わせた注入（DI）を前提としています。

---

## 自動環境読込の挙動

- 起動時、プロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索し、以下の順で読み込みます:
  1. OS 環境変数（既存の値は保護）
  2. .env（OS にない変数をセット）
  3. .env.local（既存の OS 環境変数を保護しつつ .env.local で上書き可能）

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとこの自動ロードがスキップされます。

- .env のパースはシェル風の export / コメント / クォートを考慮します。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite 永続層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - alert_manager.py — LINE 通知
    - kill_switch.py — フラグファイル停止
    - monitoring_engine.py — ポーリング統合
    - streamlit_dashboard.py — Streamlit ダッシュボード
    - __init__.py
  - execution/
    - broker_api.py — ブローカ API 抽象・データモデル・例外
    - order_manager.py — 注文作成 / 送信 / 同期
    - execution_engine.py — Signal Queue 型発注エンジン
    - reconciler.py — 起動時リコンシリエーション
    - その他: order_repository, order_record, risk_manager 等（実装に依存）
  - monitoring/, portfolio/, research/, ai/ ... の各 __init__ により主要関数をエクスポート

---

## 開発メモ / 実運用注意点

- AI 呼び出しはネットワークエラーやレート制限を考慮したリトライ実装が入っていますが、API キーは適切に管理してください。
- ニュース NLP / レジーム判定は外部 API を使うため、料金・レート制限・レスポンスの不確実性がある点に注意。
- ExecutionEngine は kill.flag / PID 管理を行います。kill.flag により外部から安全にエンジン停止が可能です。
- Reconciler は起動時の状態不整合を検出・是正する目的で設計されています。OrderSent 等の中間状態が残る事象に対処します。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し明示的にテスト用設定を注入することを推奨します。
- DB スキーマ／DuckDB テーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）は運用前に作成しておいてください（本 README ではスキーマ定義は割愛）。

---

## さらに詳しく

各モジュールの docstring に仕様や設計意図、制約・注意点がまとまっています。実装を読むことで詳細な挙動（例: 端数処理、スケーリングアルゴリズム、API のエラーハンドリング方針）を把握できます。

---

質問や README に追加してほしい具体的な実行例（例: ExecutionEngine を実際に起動する最小構成コード、DuckDB スキーマ例など）があれば教えてください。必要に応じてサンプルスクリプトを追加します。