# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants） → データ品質チェック → ファクター算出 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログまで、バックテスト／運用で必要な機能を一通り提供します。

---

## 主な機能 (Features)

- データ収集（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション・冪等保存対応）
  - レート制限／リトライ／トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを統合した日次ETL (`run_daily_etl`)
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出し QualityIssue を返却
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、SSRF 対策、記事の前処理、raw_news への冪等保存準備
- ニュースNLP（OpenAI）
  - 銘柄別ニュース集約 → LLM（gpt-4o-mini, JSON mode）へ投げてセンチメント（ai_score）を算出し `ai_scores` へ保存 (`score_news`)
  - レート制限・429/タイムアウト/5xx に対する指数バックオフ、結果バリデーション、部分失敗保護
- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュースセンチメントを合成してレジーム（bull/neutral/bear）を判定し `market_regime` に書き込み (`score_regime`)
  - Look-ahead bias を避ける設計（date 引数ベース）
- 研究用ユーティリティ
  - モメンタム・バリュー・ボラティリティのファクター算出、将来リターン計算、IC（Spearman）や統計サマリー、Z-score 正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等、発注フローを UUID でトレースする監査テーブルの初期化ユーティリティ
- 設定管理
  - `.env` ファイル自動読み込み（プロジェクトルート検出） & 環境変数経由で設定 (`kabusys.config.settings`)

---

## 要件 (Requirements)

- Python 3.10 以上（型記述に `|` 演算子などを使用）
- 推奨パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ、urllib 等

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じてプロジェクトを開発モードでインストール
pip install -e .
```

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

---

## 環境変数 / 設定

自動読み込み機能:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。
- 自動読み込みを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な環境変数:
- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabuステーション API
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に省略可）
- Slack（通知等）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
- データベースパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用途など）
- その他
  - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - LOG_LEVEL: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=hogehoge
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成 & パッケージインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をエクスポートします。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB（データベース）の準備
   - デフォルトパスは `data/kabusys.duckdb`。親ディレクトリがなければ自動作成するコードも含まれますが、先にディレクトリ用意しておくと安心です。

5. 監査 DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（代表的な API の例）

以下は Python REPL やスクリプトでの利用例です。すべて `duckdb` コネクションを渡して使います。

- 日次 ETL を実行する（データ取得・チェック）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュース NLP スコアリング（特定日）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（既存コネクションに追加）:
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ニュース RSS を取得する（collector の内部ユーティリティ）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI コールを伴う機能（score_news, score_regime）は OPENAI_API_KEY を環境変数で用意するか、関数の api_key 引数で渡してください。
- 多くの処理は Look-ahead bias 回避のため `target_date` を明示的に渡す設計です。内部で date.today() を参照しない点に留意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールは `src/kabusys` 配下に配置されています。主なファイル／モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    -- 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得/保存ロジック）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult エクスポート
    - news_collector.py     -- RSS 取得・前処理
    - calendar_management.py-- マーケットカレンダー・営業日ロジック
    - quality.py            -- データ品質チェック
    - stats.py              -- 統計ユーティリティ（zscore）
    - audit.py              -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    -- モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py-- 将来リターン / IC / 統計サマリー 等
  - ai/__init__.py
  - research/__init__.py

（README 用に省略しているファイル・補助モジュールが他にもあります）

---

## 設計上の注意点 / ポイント

- Look-ahead bias 対策が各所で施されています（明示的な target_date、DB クエリにおける `< target_date` 等）。
- API 呼び出し（J-Quants / OpenAI）にはリトライ・バックオフロジックが組み込まれ、失敗時はフェイルセーフで部分的に継続する設計です（完全な失敗を上位で検知可能）。
- DuckDB を用いた冪等保存（ON CONFLICT DO UPDATE）を多用しているため、ETL の再実行が安全に行えます。
- news_collector は SSRF / XML Bomb / Gzip Bomb などセキュリティ対策を考慮した実装になっています。

---

もし README の補足（例: 実行スクリプト、CI 設定、より詳しい .env.example のテンプレートなど）が必要であれば、必要な内容を教えてください。