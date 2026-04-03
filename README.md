# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ用ユーティリティ群をまとめたライブラリです。J-Quants / kabuステーション / OpenAI 等と連携し、データ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログなどを提供します。

## 主要機能
- データ ETL（J-Quants からの株価・財務・市場カレンダーの差分取得・保存）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）とニュース NLP（OpenAI で銘柄別センチメント算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー など）
- 監査ログ（signal → order_request → executions を追跡する監査スキーマ）
- DuckDB ベースの保存・冪等保存ロジック、J-Quants API のレート制御と再試行

---

## 必要条件・依存パッケージ（例）
主に以下が必要です（環境や将来の変更により増減する可能性があります）。
- Python 3.9+
- duckdb
- openai
- defusedxml

インストール例（最低限）:
```bash
python -m pip install duckdb openai defusedxml
# または開発中にパッケージとして使う場合
python -m pip install -e .
```

---

## 環境変数 / 設定
自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。必須・代表的な環境変数:

- JQUANTS_REFRESH_TOKEN  ← J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      ← kabuステーション API パスワード（必須）
- OPENAI_API_KEY         ← OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_BASE_URL      ← kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            ← DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            ← 監視用 SQLite（デフォルト: data/monitoring.db）
- その他（LOG_LEVEL, KABUSYS_ENV 等）

サンプル `.env`（プロジェクトルートに置く例）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

設定は `kabusys.config.settings` からアクセスできます（プロパティとして参照）。

---

## セットアップ手順（簡易）
1. リポジトリをクローン / パッケージを配置
2. 依存パッケージをインストール:
   ```
   python -m pip install duckdb openai defusedxml
   ```
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB ファイル保存先のディレクトリが存在しない場合は作成（多くの初期化関数は自動作成します）

---

## 基本的な使い方（スニペット集）

- DuckDB 接続と settings の例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（株価 / 財務 / カレンダー 取得 + 品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（ai スコア算出）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または引数で指定可
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # あるいは別パスを指定
```

- RSS 取得（ニュース収集の低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a['id'], a['title'], a['datetime'])
```

注意:
- AI 関連の関数（score_news, score_regime）は OpenAI キーが必要です。環境変数 `OPENAI_API_KEY` を設定するか、関数の `api_key` 引数で明示的に渡してください。
- J-Quants API 呼び出しは `JQUANTS_REFRESH_TOKEN` を必須とします（`kabusys.config.settings.jquants_refresh_token`）。

---

## 推奨運用メモ
- 自動ロードされる `.env` はプロジェクトルート（.git または pyproject.toml を基準）で検索されます。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- J-Quants のレートリミット（120 req/min）に合わせた内部 RateLimiter が実装されています。API 呼び出しを連続して大量に行う際は注意不要ですが、外部の追加処理で過負荷をかけないでください。
- LLM 呼び出しは再試行ロジックを持ち、失敗時には安全に 0.0 スコアにフォールバックする設計です（フェイルセーフ）。

---

## ディレクトリ構成（主要ファイル）
（パッケージルート: src/kabusys 以下）

- kabusys/
  - __init__.py               — パッケージ定義（__version__）
  - config.py                 — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（銘柄別スコア算出）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py       — RSS 収集・前処理・保存ユーティリティ
    - calendar_management.py  — マーケットカレンダー管理・営業日ロジック
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - etl.py                  — ETLResult の公開再エクスポート
    - audit.py                — 監査ログテーブル初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー等
  - ai/, data/, research/ はそれぞれのユースケース（実運用・リサーチ・AI）を分離

---

## 例: よく使う API の概要
- run_daily_etl(conn, target_date, id_token=None, ...): 日次 ETL を実行して ETLResult を返す
- score_news(conn, target_date, api_key=None): ニュースを集約して ai_scores に書き込む
- score_regime(conn, target_date, api_key=None): market_regime テーブルへレジームを書き込む
- fetch_daily_quotes / save_daily_quotes: J-Quants からの株価取得と保存
- init_audit_db(path) / init_audit_schema(conn): 監査ログの初期化

---

## 開発・テスト上の注意
- モジュールはルックアヘッドバイアスを避ける設計（内部で date.today() / datetime.today() を安易に参照しない）になっています。バックテストや日次バッチ実行時は `target_date` を明示的に渡してください。
- テスト時は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることが推奨されます。各モジュールはテスト用に内部 API 呼び出しを差し替えやすく実装されています（関数の差し替えや patch を想定）。

---

README に書かれていない細かい使い方やパラメータは、個々のモジュールの docstring を参照してください（例: kabusys/data/pipeline.py, kabusys/ai/news_nlp.py, kabusys/data/jquants_client.py など）。必要であればサンプルスクリプトや CLI ラッパーのテンプレートも作成できます — 希望があれば教えてください。