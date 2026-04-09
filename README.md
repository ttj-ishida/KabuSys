# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ、マーケットカレンダー管理、品質チェックなど、取引システムと研究環境に必要な共通機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API を用いた株価日足、財務データ、JPX カレンダーの差分取得（ページネーション対応、リトライ、レート制限）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL エントリポイント（run_daily_etl）

- ニュース収集・NLP
  - RSS フィードからのニュース収集（SSRF 対策、トラッキングパラメータ除去、正規化）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング（銘柄ごと・バッチ処理、JSON Mode 利用）
  - マクロニュース + ETF（1321）MA200 を組み合わせた市場レジーム判定

- リサーチ / ファクター
  - Momentum / Volatility / Value 等の定量ファクター計算（DuckDB に基づく）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損データ、スパイク（急変）、重複、日付不整合（未来日・非営業日）検出

- 監査ログ（トレーサビリティ）
  - 信号 → 発注リクエスト → 約定 までの監査用テーブル定義・初期化（DuckDB）
  - 冪等キー（order_request_id 等）による重複防止

- 設定管理
  - .env ファイルと OS 環境変数からの設定読み込み（自動ロード、無効化オプションあり）

---

## 必要条件（前提）

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（パッケージ化済みプロジェクトでは `pyproject.toml` / `requirements.txt` を参照してください。上記はコードから読み取れる主要依存です。）

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements ファイルがある場合はそれを利用）

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（*.local の優先ロードもあり）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

5. 必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API 用パスワード（必須）
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime を使う場合）
   - （その他）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用途、任意）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（paper_trading 時の挙動: instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

例 `.env`（抜粋）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下はライブラリをプログラムから利用する簡単な例です。

- DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム（ETF 1321 + マクロニュース）をスコアリング
```python
from kabusys.ai.regime_detector import score_regime
# conn は DuckDB 接続
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- RSS を取得して raw_news に保存するワークフロー（概要）
  - `kabusys.data.news_collector.fetch_rss(url, source)` で記事一覧を取得し、
  - 取得記事を DB に保存するロジックを組み合わせる（save は実装例に従ってください）

- 監査テーブル初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
# conn は DuckDB 接続
records = calc_momentum(conn, target_date=date(2026,3,20))
```

注意:
- 各関数は外部 API のキー（OpenAI / J-Quants）を引数で受け取れる場合があります（テスト容易性のため）。未指定時は環境変数を参照します。
- ライブラリはルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を直接参照しない設計の関数が多くあります。必ず `target_date` を明示することを推奨します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API パスワード
- OPENAI_API_KEY (score_news / score_regime を使う場合必須)
- KABU_API_BASE_URL (オプション) : デフォルト "http://localhost:18080/kabusapi"
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用、任意)
- DUCKDB_PATH (オプション) : デフォルト data/kabusys.duckdb
- SQLITE_PATH (監視用、オプション) : デフォルト data/monitoring.db
- PAPER_FILL_MODE (paper_trading 用) : instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH : デフォルト data/paper_trading.db
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（銘柄別 ai_scores 生成）
  - regime_detector.py — マクロ + ETF MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存 / 認証 / リトライ / レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 定義
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集・前処理・SSRF 対策・ID 正規化
  - calendar_management.py — JPX カレンダー管理・営業日判定・calendar_update_job
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — zscore 正規化など統計ユーティリティ
  - audit.py — 監査ログ（DDL / テーブル初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

各モジュールは設計方針コメントと共に実装されており、バックテストや本番環境での誤用を避けるためにルックアヘッドバイアス対策が施されています。

---

## 開発・テストメモ

- OpenAI 呼び出しやネットワーク I/O 部分はテスト容易性のため差し替え（mock）できるように設計されています（モジュール内の `_call_openai_api` 等を patch）。
- .env の読み込みはプロジェクトルートを親ディレクトリから探索して行うため、パッケージ配布後も動作するよう配慮されています。
- DuckDB の executemany は空リストでの呼び出しに注意（コード内で明示的に空チェックがあります）。

---

必要ならば、README にサンプル .env.example、より詳細な API 使用例、あるいは運用上の注意（バックテストでのデータ受け渡し方法など）を追加できます。どの部分を詳しく書けばよいか教えてください。