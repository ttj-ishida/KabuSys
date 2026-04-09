# KabuSys

日本株向けの自動売買サブシステム群（ライブラリ & 実行エンジン）。  
ポートフォリオ構築・ポジションサイズ決定、ファクター計算、ニュースの NLP スコアリング、マーケットレジーム判定、監視（モニタリング）および発注実行エンジンなどを備えています。モジュールは可能な限り純粋関数／副作用を分離した設計になっており、DuckDB / SQLite をデータ層に使用します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 設定管理
  - .env / .env.local / OS 環境変数からの自動ロード（プロジェクトルート検出）
  - 必須環境変数の検証
- ポートフォリオ構築
  - 候補選定（スコアソート）
  - 等重・スコア重み・リスクベース配分
  - セクター集中上限フィルタ、レジーム乗数
- ポジションサイズ計算
  - 単元株丸め、max position / aggregate cap、コストバッファ適用
- 研究用ファクター計算
  - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20）、Value（PER/ROE）
  - 将来リターン計算、IC（スピアマン）やファクター統計サマリ
- AI（LLM）連携
  - ニュース記事の銘柄別センチメント評価（OpenAI）
  - マクロニュースとETF MA200 を組み合わせた市場レジーム判定
  - レート制限 / リトライ / バリデーションを実装
- 実行（Execution）
  - Signal Queue ベースの発注エンジン（ExecutionEngine）
  - OrderManager / OrderRepository を用いた堅牢な状態遷移と再同期（Reconciler）
  - Broker API 抽象（Protocol）と例外モデル
- 監視（Monitoring）
  - SQLite ベースの監視 DB（init 用スクリプトあり）
  - System / Trade / Risk モニタ、Kill Switch、LINE 通知（AlertManager）
  - Streamlit ダッシュボード（読み取り専用で可視化）

---

## 必要条件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- requests
- psutil
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）

例（pip）:
```bash
pip install duckdb openai requests psutil streamlit
```

プロジェクトに requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt  # もしあれば
   # または最低限:
   pip install duckdb openai requests psutil streamlit
   ```
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` / `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する .env の例:
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

# 任意（デフォルトが使われるもの）
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

重要: Settings クラスは `.env` 読み込みロジックと OS 環境を組み合わせて扱います。保護された OS 環境変数は `.env.local` で上書きされますが、既存の OS 環境変数は上書かれません（protected 機構）。

---

## 主要な環境変数（抜粋・説明）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_FILL_MODE — paper trading の fill 動作（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行制御用のファイルパス
- KABUSYS_ENV — 環境: development / paper_trading / live

注意: Settings は必須キー未設定時に ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## 使い方（代表的な例）

- DuckDB コネクションの作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 研究（ファクター計算）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)       # 各銘柄の momentum
vol = calc_volatility(conn, d)     # ATR, avg_turnover 等
val = calc_value(conn, d)          # PER, ROE
```

- ファクター探索・IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_5d")
```

- ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026,3,20), api_key="sk-...")
print(f"wrote {n_written} scores to ai_scores")
```

- 市場レジーム判定（regime）
```python
from kabusys.ai.regime_detector import score_regime
res = score_regime(conn, date(2026,3,20), api_key="sk-...")
```

- ポートフォリオ構築ユーティリティ
```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
sizes = calc_position_sizes(weights, candidates, portfolio_value=1_000_000, available_cash=700_000, ...)
```

- 監視 DB 初期化
```python
import sqlite3
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

- Streamlit ダッシュボード（起動コマンド）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ExecutionEngine の概略（本番的な流れ）
  - Reconciler で再同期（起動時）
  - signal_send_start（デフォルト 08:50）にシグナル読み込み＋発注（Gate チェック）
  - WebSocket push をデーモンで受け取り約定同期
  - market_close（デフォルト 15:30）で終了
  - 実行例は ExecutionEngine クラスを参照し、Broker 実装・OrderRepository 等を DI してください。

---

## 注意点・設計に関する注記

- 多くのモジュールは副作用を極力排し、DuckDB/SQLite のみを参照する関数はテストしやすく設計されています（例: research モジュール、portfolio モジュール）。
- AI 呼び出しは堅牢性を重視し、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフを行います。レスポンスは厳密な JSON の期待と検証処理があります。
- Execution / OrderManager はクラッシュ安全性を考慮した 2 段階永続化や Reconciler を備えています。
- 自動 .env ロード:
  - プロジェクトルートはこのパッケージの __file__ を起点に `.git` または `pyproject.toml` を探索して決定します。CWD に依存しません。
  - OS 環境 > .env.local > .env の優先順位で読み込みます。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロ NLP）
- portfolio/
  - __init__.py
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 発注株数計算
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value 等
  - feature_exploration.py — 将来リターン / IC / サマリ
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite スキーマ・MonitoringDB
  - system_monitor.py — CPU/メモリ/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 監視の統合エンジン
  - streamlit_dashboard.py — Streamlit ベースの可視化
- execution/
  - broker_api.py — Broker API データモデル / Protocol / 例外
  - execution_engine.py — Signal Queue ベース発注エンジン
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — Order State Machine の外向け API
  - （他に order_repository / order_record 等が存在する想定）
- monitoring/（上に同じ）
- research/（上に同じ）

※上記はコードベース抜粋に基づく主要ファイル一覧です。実際のソースツリーには他ファイル（order_repository / order_record / data パイプライン等）が含まれることが想定されます。

---

## 開発 / テストのヒント

- AI 周りのテストでは OpenAI クライアント呼び出しをモック（patch）する設計になっています（news_nlp._call_openai_api / regime_detector._call_openai_api 等）。
- DuckDB / SQLite に対してはテスト用の一時ファイル（in-memory も可）を用いると再現性が高いです。
- `.env` の自動ロードはプロジェクトルート検出に依存するため、テスト時に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うか、期待する .env ファイルの配置に注意してください。

---

この README はコードベースの主要部分を簡潔にまとめたものです。具体的な利用シナリオ（ブローカー実装、注文リポジトリ、signal queue の接続方法など）はプロジェクト内の該当ドキュメント / モジュールコメントを参照してください。必要であれば、特定モジュールの使用例や API リファレンスを追記します。