# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株向けのデータプラットフォーム / 研究 / 監査 / AI 支援スコアリングを提供する Python モジュール群です。J‑Quants API からのデータ取得（株価・財務・市場カレンダー）、DuckDB を使った ETL、ニュースの収集・NLP スコアリング（OpenAI 経由）、研究用ファクター計算、監査ログ（注文 → 約定トレース）など、自動売買システムの基盤処理を幅広くサポートします。

主な設計方針：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() に依存しない実装）
- DuckDB によるローカル永続化と効率的な SQL 処理
- 外部 API 呼び出しはリトライ / レート制御を伴う安全実装
- フェイルセーフ（API 失敗時はデフォルト値で継続）で運用向けを意識

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート探索）および settings オブジェクト
- データ ETL（J‑Quants）
  - 株価日足（raw_prices）の差分取得 / 保存
  - 財務データ（raw_financials）の差分取得 / 保存
  - 市場カレンダー（market_calendar）の差分取得 / 保存
  - ETL パイプライン（run_daily_etl）と品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化（トラッキング除去）、SSRF 対策、raw_news への冪等保存想定
- ニュース NLP（OpenAI）
  - 銘柄単位のニュース統合センチメント（score_news）
  - マクロニュースと ETF（1321）の MA200 を組み合わせた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Spearman）計算、Z スコア正規化
- 監査ログ（オーダー・約定トレーサビリティ）
  - 監査テーブル定義および初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 前提（推奨環境）

- Python 3.10 以上（型注釈に PEP 604 の `|` を使用）
- 必要パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（他に標準ライブラリのみで多くを実装しています。運用用途では logging 等の設定や sqlite3 などの環境が別途必要な場合があります）

---

## インストール

プロジェクトルート（pyproject.toml / setup が存在する場所）でパッケージをインストールします。開発時は editable install を推奨します。

例（pip）:
```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# 必要パッケージをインストール
pip install duckdb openai defusedxml

# 開発インストール（プロジェクトに setup/pyproject がある前提）
pip install -e .
```

---

## 環境変数（.env）

KabuSys は実行時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で自動読み込みを行います（OS 環境変数を優先）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（.env に含める例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

settings オブジェクトで上記を参照できます：
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. 初期 DB を作成（必要に応じて）
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メイン DuckDB を手動で作成して schema 初期化等の処理を行う（プロジェクトに schema 初期化スクリプトがある想定）

---

## 使い方（代表的な例）

以下では Python REPL / スクリプト内での例を示します。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print("written:", num_written)
```

- 市場レジーム判定（ETF 1321 MA200 とマクロニュースの統合）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しはリトライ・バックオフや JSON モードを利用して冗長性を抑えていますが、API キーのレートやコストには注意してください。
- J‑Quants API 呼び出しはレート制御（120 req/min）や自動トークンリフレッシュを行います。`JQUANTS_REFRESH_TOKEN` を正しく設定してください。
- ETL や AI スコアリング関数はルックアヘッドバイアスを避ける設計（明示的 target_date）です。バッチ実行時は target_date を適切に指定してください。
- DuckDB の `executemany` はバージョンによる制約があるため、実装側で空リスト回避等の配慮があります。DuckDB のバージョン互換性に注意してください。
- `.env.local` は `.env` より優先して上書きされます。OS 環境変数は最優先です。
- 自動 env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

---

## ディレクトリ構成（主要ファイル）

例: src/kabusys 以下のモジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLU / OpenAI 呼び出し、score_news
    - regime_detector.py     — ETF MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J‑Quants API クライアント・保存ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETル公開インターフェース（ETLResult 等）
    - news_collector.py      — RSS 収集、テキスト前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - quality.py             — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン, IC, factor_summary, rank

（上記以外に strategy / execution / monitoring 等のパッケージが定義される想定）

---

必要に応じて README に入れたい追加情報（CI、テスト実行方法、具体的な schema 初期化方法、運用手順など）があれば教えてください。README を運用手順や API リファレンス中心に拡張できます。