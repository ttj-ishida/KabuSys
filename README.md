# KabuSys

日本株自動売買システムのライブラリ群（モジュール集合）。ポートフォリオ構築、ファクター計算、AI によるニュース/レジーム判定、発注エンジン、監視（ログ永続化・アラート・ダッシュボード）などを含む。

---

## 概要

KabuSys は以下のような機能を持つモジュール設計のライブラリです。

- DuckDB / SQLite を用いたデータ処理・永続化（価格データ、財務データ、監視ログ等）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ファクター探索・IC 計算などのリサーチユーティリティ
- ニュースを LLM（OpenAI）でスコアリングする NLP パイプライン
- ETF + マクロニュースを使った市場レジーム判定（LLM と組み合わせ）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイズ算出）
- 発注エンジン（OrderManager / ExecutionEngine / Reconciler 等、Broker API 抽象化）
- 監視機能（system / trade / risk の監視、LINE によるアラート、streamlit ダッシュボード）
- テストしやすい純粋関数設計（多くは DB 参照を明示的に受け取る）

設計思想の要点：
- ルックアヘッドバイアス回避（関数は日付引数を受け取り datetime.today() を自発的に参照しない設計）
- 副作用の制御（DB 接続や API クライアントを引数で注入）
- フェイルセーフ（AI / 外部 API 失敗時は安全側のフォールバック）

---

## 主な機能一覧

- kabusys.config — 環境変数 / .env 読み込み（.env, .env.local をプロジェクトルートから自動読み込み、優先度: OS 環境 > .env.local > .env）
- kabusys.research — calc_momentum / calc_volatility / calc_value、forward return / IC / summary
- kabusys.portfolio — 候補選定、等重・スコア重み、リスク調整（セクター上限）、ポジションサイズ計算
- kabusys.ai.news_nlp — raw_news を LLM で評価して ai_scores に書き込む
- kabusys.ai.regime_detector — ETF + マクロニュースで日次レジーム判定
- kabusys.execution — Broker API 抽象、OrderManager、ExecutionEngine、Reconciler、リスク管理連携
- kabusys.monitoring — MonitoringDB（SQLite）、各種モニタ、KillSwitch、AlertManager（LINE push）、streamlit ダッシュボード

---

## 前提条件 / 必要パッケージ

（このリポジトリに requirements.txt がない場合は適宜追加してください。想定される主な依存）

- Python 3.10+（型注釈で union 型などを使用）
- duckdb
- openai（OpenAI の公式 SDK）
- requests
- psutil
- streamlit（ダッシュボード用）
- sqlite3（標準ライブラリ）
- その他：typing, dataclasses, logging 等は標準ライブラリ

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

---

## 環境変数 / .env キー一覧

下記の環境変数がコード中で参照されます。運用環境に合わせて `.env` を作成してください（Settings が必須チェックするキーもあります）。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード

OpenAI（AI 機能を使う場合）:
- OPENAI_API_KEY — OpenAI API キー

LINE 通知（監視アラート用、任意）:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

DB / パス系:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）

運用フラグ / チューニング:
- PAPER_FILL_MODE — paper trading の fill モード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（1 = クリア）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値パーセント
- KABUSYS_ENV — 環境ラベル（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env の読み込みをスキップします（テスト用等）。

.env 読み込みの特徴:
- プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して決定します（CWD に依存しない）。
- .env のパースはシェル風:
  - コメント（#）対応、`export KEY=val` 形式対応、シングル/ダブルクォート対応（エスケープ処理）
  - 読み込み優先度: OS 環境 > .env.local > .env
  - .env.local は上書き（override=True）され、ただし OS 環境で既に定義されたキーは上書きされません（protected 機構）

---

## セットアップ手順（簡易）

1. レポジトリをチェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、必要な環境変数を設定
4. データディレクトリを作成
```bash
mkdir -p data
```
5. 監視 DB 初期化（MonitoringDB テーブルを作成）
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
conn.close()
```
6. DuckDB データファイル（prices_daily / raw_financials / raw_news 等）を準備する（ETL / pipeline は別途実装）

---

## 使い方（代表的な利用例）

- 設定参照:
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.sqlite_path)
```

- ファクター計算（research）:
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
res_mom = calc_momentum(conn, date(2026, 3, 20))
res_vol = calc_volatility(conn, date(2026, 3, 20))
res_val = calc_value(conn, date(2026, 3, 20))
```

- 将来リターン / IC / 統計サマリ:
```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
fwd = calc_forward_returns(conn, date(2026,3,20))
ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_1d")
summary = factor_summary(factor_records, ["mom_1m", "mom_3m", "per"])
```

- ニューススコアリング（OpenAI 必須）:
```python
from kabusys.ai.news_nlp import score_news
# conn は duckdb 接続、target_date は評価日
n_written = score_news(conn, target_date, api_key="sk-...")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date, api_key="sk-...")
```

- 監視ダッシュボード（streamlit）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- 監視 DB を利用した書き込み（MonitoringDB の使用例はモジュール内のクラス参照）:
```python
import sqlite3
from kabusys.monitoring.monitoring_db import MonitoringDB

conn = sqlite3.connect("data/monitoring.db")
db = MonitoringDB(conn)
db.log_system_status(cpu_percent=10.0, memory_percent=30.0, disk_percent=40.0, process_ok=True)
```

- ExecutionEngine / OrderManager / Broker API:
  - 実運用では BrokerAPIProtocol に準拠する具体的なクライアント（kabuステーション等）を実装し、OrderRepository（SQLite 実装）を渡して ExecutionEngine を構成します。
  - このリポジトリではエンジンのロジックが実装されていますが、ブローカー側接続を追加で実装する必要があります（抽象化された Protocol を参照）。

---

## 開発者向けメモ

- 多くの関数は DB 接続（duckdb.DuckDBPyConnection）を引数に受け取り、外部 API 呼び出しを直接行わない設計です（安全なテストが可能）。
- AI 呼び出し部分（news_nlp, regime_detector）は OpenAI SDK の例外（429, 接続エラー, タイムアウト, 5xx）に対して指数バックオフでリトライする実装です。失敗時はフェイルセーフ（0.0 等）で継続します。
- .env パーサはシェルスタイルのエッジケース（クォート内のエスケープ、export_, inline コメント）に対応します。
- MonitoringDB のマイグレーションや streamlit ダッシュボードは軽量で、既存 DB に対するカラム追加等の互換処理も含みます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / .env の読み込みと Settings クラス
- portfolio/
  - portfolio_builder.py — 候補選定、等重/スコア重み
  - position_sizing.py — 株数算出、aggregate cap 調整
  - risk_adjustment.py — セクター上限適用、レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value ファクター計算
  - feature_exploration.py — forward returns, IC, summary utilities
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF + マクロニュース + OpenAI）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 / MonitoringDB クラス
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定価格異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 各モニタのポーリング統括
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
- execution/
  - broker_api.py — Broker API のデータモデル / Protocol / 例外
  - order_manager.py — OrderManager（作成・送信・同期・キャンセル）
  - execution_engine.py — Signal Pull 型の発注エンジン（セッション管理）
  - reconciler.py — 起動時リコンシリエーション
  - （その他 OrderRepository / OrderRecord 等は別ファイルに存在）
- monitoring/..., research/..., portfolio/...（上記に詳細）

---

## テスト / 開発

- 各モジュールは外部依存（DB 接続、Broker、OpenAI クライアント等）を引数で受けるため、ユニットテストではモック注入が容易です。
- news_nlp.py や regime_detector.py の OpenAI 呼び出しは内部関数を patch して差し替え可能（テスト用に設計済み）。

---

もし README に追記したい具体的な手順（CI 設定、requirements.txt、サンプルデータの作成スクリプト、Broker 実装ひな形など）があれば教えてください。必要に応じてサンプルコマンドや例を追加します。