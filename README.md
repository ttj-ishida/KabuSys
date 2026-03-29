# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー収集）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどのユーティリティを提供します。

## 主な機能
- ETL（data.pipeline）
  - J-Quants API から株価日足 / 財務データ / マーケットカレンダーを差分で取得・保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF / XML Bomb / 大容量レスポンス等の安全対策あり
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア生成（ai_scores へ保存）
  - バッチ処理、リトライ、レスポンス検証を実装
- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- データ品質チェック（data.quality）
  - 欠損・重複・スパイク・日付不整合検出（QualityIssue を返す）
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義・初期化ユーティリティ

---

## 必要条件
- Python 3.10+
  - 型注記に Python 3.10 の Union 表記（|）を使用しています。
- 主な依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
pip install duckdb openai defusedxml
```
（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数 / 設定
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動読み込み）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（実行する機能に応じて）:
- J-Quants
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- kabuステーション（発注を行う場合）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack（通知を行う場合）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

オプション / その他:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY : OpenAI API キー（ai モジュールで使用）

注意:
- `.env.local` は `.env` より優先して読み込まれ、OS 環境変数はさらに優先されます。
- 環境変数参照は `kabusys.config.settings` を通じて行います。

---

## セットアップ手順（開発者向け）
1. リポジトリをクローンし、仮想環境を作成・有効化
2. 必要パッケージをインストール
   - 例: pip install -r requirements.txt（プロジェクトにあれば）  
   - または個別: pip install duckdb openai defusedxml
3. プロジェクトルートに `.env` を作成（例は下記）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - 実運用では `.env.local` を使って機密値を上書きすることができます。
4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な機能の例）

- DuckDB 接続を作る（settings を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（ai.news_nlp）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored:", n_written)
```

- 市場レジームスコアを計算して保存（ai.regime_detector）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn にテーブルを追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- ニュース RSS を取得（単体）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

実運用上の注意:
- AI（OpenAI）呼び出しはレートやコストを伴うため、API キー管理とログ記録に注意してください。
- 各モジュールはルックアヘッドバイアス防止のため、内部で `date.today()` 等を直接参照しない設計になっています（呼び出し側で date を渡すことが推奨されます）。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主なモジュールと役割の一覧です。

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / 設定の読み込み
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（OpenAI） & ai_scores 書き込み
    - regime_detector.py  — マクロ + MA200 を使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py   — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダーの管理 / 営業日計算
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py          — データ品質チェック群
    - audit.py            — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py  — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記は主要モジュールのみを抜粋した構成です）

---

## 設計上の要点 / 運用上の注意
- ルックアヘッドバイアス対策が随所に組み込まれています（関数に target_date を明示して使う設計）。
- J-Quants クライアントはレートリミット・リトライ・401 時の自動トークンリフレッシュを実装しています。
- ニュース収集は SSRF や XML 攻撃、巨大レスポンスなどへの対策が施されています。
- OpenAI 呼び出しはリトライ・レスポンスのバリデーション（JSON mode を想定）を行い、失敗時はフォールバック挙動（0.0 など）を取ることでフェイルセーフにしています。
- DuckDB への書き込みは冪等性を重視（ON CONFLICT DO UPDATE 等）しています。

---

## 補足 / 開発時のヒント
- 自動で .env をロードしますが、ユニットテストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動読み込みを抑止できます。
- OpenAI 呼び出しのテストは各モジュールの `_call_openai_api` をモックする想定で実装されています。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン（例: 0.10）に配慮した実装が散見されます。呼び出し時は注意してください。

---

必要であれば、README に含める具体的な .env.example、requirements.txt の推奨セット、もしくは典型的な運用ワークフロー（ETL → ニューススコア → レジーム判定 → 発注）を追記します。どの情報を詳細化しますか？