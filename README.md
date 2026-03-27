# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター研究、監査ログ、マーケットカレンダー管理、発注監視などのユーティリティを提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（OHLCV）／財務データ／JPX カレンダーを差分取得し DuckDB に冪等保存
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、URL 正規化、トラッキングパラメタ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント）→ market_regime 保存（score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC（情報係数）計算、統計サマリー、Z スコア正規化

- 監査ログ（オーダー/シグナル監査）
  - signal_events / order_requests / executions テーブル定義、インデックス、初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注トレーサビリティ確保（UUID / 冪等キー設計）

- 設定管理
  - .env / .env.local / 環境変数の自動読み込み（プロジェクトルート検出）
  - Settings クラス経由で設定値を取得（kabusys.config.settings）

---

## 必要要件（例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

（実際のパッケージ要件はプロジェクトの packaging / requirements を参照してください）

例（最小）:
pip install duckdb openai defusedxml

---

## 環境変数 / .env

自動的にプロジェクトルート（.git または pyproject.toml を探索）で `.env` と `.env.local` をロードします。読み込み順は OS 環境変数 > .env.local > .env です。テストなどで自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須なものがいくつかあります）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 使用時に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: one of development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

必須パラメータは `kabusys.config.settings` 経由で取得すると例外で明示的に通知されます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があれば pip install -e . や pip install -r requirements.txt を使用）

4. .env を作成
   - リポジトリルートの `.env.example` を参考に `.env` を作成し、必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定します。
   - 開発用の上書きは `.env.local` に記載できます（.env.local は .env より優先して読み込まれます）。

5. DuckDB・監査 DB の初期化（必要に応じて）
   - Python から init_audit_db を呼び出すか、監査テーブルを既存 DuckDB 接続に追加します（後述サンプル参照）。

---

## 使い方（基本サンプル）

以下は Python スクリプト／インタラクティブでの利用例です。import はパッケージ名 `kabusys` を想定しています。

1) ETL（日次 ETL）の実行例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB 接続（settings.duckdb_path を利用する例）
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 今日分の ETL を実行（id_token を外部で取得済みなら渡せます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（AI）例
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を参照
print(f"scored {count} tickers")
```

3) 市場レジーム判定（AI + MA200）例
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログスキーマ初期化 / 監査 DB 作成
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn を使って order_requests 等へアクセス可能
```

5) J-Quants クライアントを直接使ってデータ取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

rows = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
print(len(rows))
```

注意:
- OpenAI 呼び出しには API キー（OPENAI_API_KEY）または各関数の api_key 引数が必要です。
- AI 呼び出しはリトライやフェイルセーフを備えていますが、API 使用量やレイテンシーに注意してください。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py : パッケージ定義、バージョン
  - config.py : 環境変数と設定管理（.env 読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py : ニュースを LLM でスコアリングして ai_scores に書き込む処理
    - regime_detector.py : ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py : 市場カレンダー管理・営業日判定・カレンダー更新ジョブ
    - etl.py : ETL インターフェース（ETLResult エクスポート）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）
    - stats.py : Z スコア正規化など統計ユーティリティ
    - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py : 監査ログテーブル定義と初期化（signal_events / order_requests / executions）
    - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py : RSS 収集・前処理・保存ユーティリティ（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py : 将来リターン・IC 計算・統計サマリー
  - monitoring / strategy / execution / （その他）: パッケージ公開一覧に含まれるが、本リードミーのコード内に含まれる主要モジュールは上記

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス回避:
  - 多くのモジュール（ETL / AI スコアリング / リサーチ）は datetime.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや再現性のために target_date を明示して実行してください。

- 環境変数の自動読み込み:
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードしますが、テストや外部プロセスから読み込みを制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

- OpenAI / J-Quants の API 呼び出し:
  - 料金やレート制限に注意してください。J-Quants クライアントは内部でレート制御および再試行を実装していますが、運用時は呼び出し頻度と課金を監視してください。

- セキュリティ:
  - news_collector は SSRF 対策や XML の無害化（defusedxml）を適用していますが、取得先の管理／アクセス許可は運用上で慎重に行ってください。

---

## 開発・テスト

- 自動ロードを無効にして環境をテストする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部 API をモックしてユニットテストを行います。コード中にモックしやすい内部呼び出し（_call_openai_api / _urlopen 等）が用意されています。

---

この README はコードベースの主要機能と利用方法をコンパクトにまとめたものです。個別の API（関数）についてはソースドキュメント（docstrings）を参照してください。必要ならサンプルスクリプトやデプロイ手順も追加できますので、希望があれば教えてください。