# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants からのデータ取得、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（オーディット）など、トレーディング・リサーチ・運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な機能

- 環境変数 / .env 読み込みと設定管理（kabusys.config）
- J-Quants API クライアント（レート制御、トークン自動リフレッシュ、リトライ付き）
  - 日次株価（OHLCV）の取得と DuckDB への冪等保存
  - 財務データ取得と保存
  - JPX カレンダー取得と保存
- ETL パイプライン（差分取得、バックフィル、品質チェックの統合）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理／保存（SSRF対策・サイズ制限あり）
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング（ai.news_nlp）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成：ai.regime_detector）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量探索（research）
- 監査ログ（signal → order_request → executions のトレーサビリティ）と初期化ユーティリティ（data.audit）

---

## 必要条件

- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

※ requirements.txt はこのリポジトリに含まれていないため、プロジェクトで必要なバージョンを固定して導入してください。

例:
pip install "duckdb" "openai" "defusedxml"

---

## セットアップ手順

1. リポジトリをクローン / コピーし、仮想環境を作成して有効化します。
   - Python 3.10+ を使用してください。

   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストールします（プロジェクト側で requirements.txt を用意している場合はそれを使用してください）。

   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定します。`.env` ファイルをプロジェクトルートに置くと自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主要な環境変数（必須となるもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合は必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite (monitoring 用) パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

   例 .env（サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベースの準備（監査ログを使用する場合）
   - 監査用 DuckDB を初期化するユーティリティが提供されています（data.audit.init_audit_db / init_audit_schema）。

---

## 使い方（代表的な例）

以下は代表的な利用例です。適宜 import して利用してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しないと今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコア取得）を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数、または api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", num_written)
```

- マーケットレジーム判定を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を既存 conn に対して呼ぶことも可能
```

- ニュース RSS を取得する（ニュース収集モジュールを単体で使う場合）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source_name, url = next(iter(DEFAULT_RSS_SOURCES.items()))
articles = fetch_rss(url, source=source_name)
for a in articles:
    print(a["id"], a["title"])
```

注意:
- OpenAI 呼び出しは rate-limit や API エラーを取り扱うリトライを持ちますが、API キーや使用制限に注意してください。
- ETL / AI 処理は外部 API を使うため通信環境や API 利用料に注意してください。

---

## 環境変数と自動 .env 読み込み

- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに便利です）。

- 必須の環境変数が足りない場合、 settings のプロパティアクセスで ValueError が発生します（例: settings.jquants_refresh_token）。

---

## ロギング／設定

- 設定は kabusys.config.Settings 経由で取得できます（settings.jquants_refresh_token, settings.duckdb_path など）。
- LOG_LEVEL 環境変数（デフォルト INFO）や KABUSYS_ENV（development / paper_trading / live）で挙動を切替可能です。
- DuckDB 接続はアプリ側で作成して関数に渡します（モジュールは接続オブジェクトを受け取って SQL を実行します）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP（銘柄別スコアリング）
  - regime_detector.py   — マーケットレジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult 再エクスポート
  - stats.py             — 統計ユーティリティ（zscore_normalize）
  - quality.py           — データ品質チェック
  - news_collector.py    — RSS ニュース収集・前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - audit.py             — 監査ログテーブル初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py   — モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー など
- monitoring/ (README に含めるためトップレベルで参照されている場合あり)
  - （モニタリング関連のモジュールはこのリポジトリで提供されているか確認してください）

---

## 設計上の注意点 / ガイドライン

- ルックアヘッドバイアスを避ける設計
  - 各モジュールは内部で datetime.today() / date.today() などに依存しない（target_date を引数として受ける）。
- DuckDB をメインの分析データベースとして使用（ETL は DuckDB に差分保存、ON CONFLICT DO UPDATE ベースで冪等性を確保）。
- 外部 API（J-Quants / OpenAI）はリトライ・バックオフや rate-limit 対応を組み込んで安全に利用。
- ニュース収集は SSRF 対策、応答サイズチェック、XML の安全パースを実装。

---

## 開発 / テストについて

- 単体テストや CI 実行時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env 読み込みを無効化すると制御しやすくなります。
- OpenAI 呼び出しやネットワーク I/O 部分はモック可能（ソース内に差し替えを想定した箇所があります）。
- DuckDB を用いるため軽量なインメモリ検証が容易です（db_path=":memory:" を渡して init_audit_db などを使えます）。

---

## ライセンス / 貢献

- この README は提供されたソースコードに基づく概略ドキュメントです。実運用前に各関数の引数・戻り値、例外挙動をソースで確認してください。
- 外部 API の利用にはそれぞれの利用規約・料金ポリシーが適用されます。API キーやトークンは安全に管理してください。

---

何か特定の機能（ETL の詳細な実行例、監査スキーマの詳細、AI スコアのプロンプト例など）について README に追記したい場合は教えてください。必要に応じてサンプル .env.example や起動スクリプト、requirements.txt のテンプレートも作成します。