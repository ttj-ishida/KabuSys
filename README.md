# KabuSys

日本株向け自動売買・データ基盤ライブラリ。J-Quants・RSS・OpenAI（LLM）などを組み合わせて
データ収集（ETL）・品質検査・ニュースNLP・市場レジーム判定・監査ログ等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下の役割を持ちます：

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL
- raw_news の収集とニュースの前処理（RSS）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄単位）とマクロセンチメント評価
- 市場レジーム（bull/neutral/bear）判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブル（signal → order_request → execution）の初期化・管理
- 研究用ファクター計算・特徴量解析ユーティリティ

設計上の重要点：
- ルックアヘッドバイアスを避けるため、日付の解決は明示的に行う（date.today() を直接参照しない関数が多い）
- DuckDB を主要なローカル DB として利用
- OpenAI / J-Quants API 呼び出しにはリトライ・バックオフ・フェイルセーフが組み込まれている

---

## 機能一覧

主な機能（モジュール別）
- kabusys.config: .env / 環境変数読み込みと Settings インターフェース
- kabusys.data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - ニュース収集（RSS → raw_news）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- kabusys.ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 → ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM スコアを合成して market_regime に保存
- kabusys.research:
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算・IC 計算・統計サマリー等

---

## 前提条件 / 必要環境

- Python 3.10 以上（型注釈に `X | Y` 構文を使用）
- 推奨パッケージ（一例）:
  - duckdb
  - openai (OpenAI Python SDK の v1 系で OpenAI クライアントが利用可能なもの)
  - defusedxml
- ネットワークアクセス: J-Quants API, RSS フィード、OpenAI API へアクセス可能であること

例（仮のインストールコマンド）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# もしプロジェクトをeditable installするなら:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／取得。
2. 仮想環境作成・依存パッケージをインストール（上記参照）。
3. プロジェクトルートに `.env` または `.env.local` を作成して環境変数を設定するか、システム環境変数に設定します。
   - 自動で .env を読み込む挙動:
     - OS 環境変数 > .env.local > .env の順で読み込みます。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を利用する場合）
   - その他（任意/デフォルトあり）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）

例 .env（最小）:
```dotenv
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的なコード例）

以下は Python スクリプトや REPL から呼び出す例です。事前に環境変数を適切に設定してください。

- DuckDB 接続の取得例:
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- 個別 ETL（株価のみ）:
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュースのセンチメントスコア算出（ai_scores へ書き込む）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")
```

- 市場レジームのスコア算出（market_regime へ書き込む）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って監査テーブルにアクセス可能
```

- カレンダーの夜間更新ジョブ呼び出し（差分取得）:
```python
from kabusys.data.calendar_management import calendar_update_job
updated = calendar_update_job(conn, lookahead_days=90)
print(f"保存したレコード数: {updated}")
```

注意点:
- OpenAI の呼び出しはコストが発生します。テスト時はモックを推奨します（コード内に patch で差し替えやすい実装になっています）。
- API レート・コストに注意してください（J-Quants: 120 req/min の制約に対応済み）。

---

## 主要な設定・振る舞い

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を読み込みます。
  - OS 環境変数は保護され、`.env.local` の override でのみ上書きします。
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- settings API（使用例）:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                — ニュースセンチメント（銘柄単位）算出
  - regime_detector.py         — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch/save）
  - pipeline.py                — ETL パイプライン（run_daily_etl 等）
  - etl.py                     — ETL の公開型（ETLResult）
  - calendar_management.py     — マーケットカレンダー管理 / 営業日判定
  - news_collector.py          — RSS 収集・前処理
  - quality.py                 — データ品質チェック
  - stats.py                   — 統計ユーティリティ（zscore 正規化）
  - audit.py                   — 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py         — ファクター計算（momentum/value/volatility）
  - feature_exploration.py     — 将来リターン・IC・統計サマリー等

---

## 注意事項 / 運用メモ

- OpenAI / J-Quants の API キーは安全に保管してください。README の例のまま公開リポジトリに置かないでください。
- LLM 呼び出しはコストとレイテンシが発生するため、本番実行時は利用頻度とバッチサイズを検討してください（実装ではバッチやリトライ処理あり）。
- テスト時はネットワーク呼び出しをモックすることで高速に検証可能です（モジュール内に差し替えやすい設計あり）。
- DuckDB のスキーマ初期化（監査テーブルなど）には init_audit_schema / init_audit_db を利用してください。

---

もし README に追加したい使い方（例えば CLI スクリプト例、Docker 構成、CI ワークフローなど）があれば教えてください。必要に応じてサンプルスクリプトや .env.example も作成できます。