# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由の価格・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）によるセンチメントスコアリング、ファクター計算・特徴量探索、監査ログ（発注／約定のトレーサビリティ）など、投資戦略の構築と運用に必要な機能群を提供します。

---

## 主要な機能
- データ取得・ETL
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを差分取得／保存（DuckDB）
  - 差分更新・バックフィル・品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策、サイズ制限、トラッキングパラメータ削除）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini, JSON mode）
  - マクロニュースの市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Zスコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions を含む監査テーブル定義と初期化ユーティリティ
  - 発注の冪等性・トレーサビリティ設計
- 設定管理
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須設定は明示的に検査

---

## 動作要件
- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他（環境に応じて）
  - urllib, json, logging など標準ライブラリ

requirements.txt（例）:
```
duckdb>=0.10
openai>=1.0
defusedxml
```

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをチェックアウト
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   # または: pip install -r requirements.txt
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   .env の例:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知など)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # OpenAI (ニュース NLP / レジーム判定で使用)
   OPENAI_API_KEY=sk-...

   # DB
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## データベース初期化（監査用 DuckDB など）

監査ログ用データベースを作成してテーブルを初期化する例:
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイル DB を作成（親ディレクトリは自動作成）
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

既存接続へ監査スキーマを追加する:
```python
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的なユーティリティ例）

以下はライブラリ内の関数を使うための簡単なサンプルです。実行前に必要な環境変数（API キー等）を設定してください。

- ETL（日次パイプライン）実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY をセット
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS フィードの取得（News Collector）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- リサーチ：モメンタム計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点:
- OpenAI 呼び出しを伴う関数（score_news, score_regime 等）は API キーの設定（引数 or OPENAI_API_KEY 環境変数）が必要です。
- 多くの関数は DuckDB 接続を直接受け取ります。接続とテーブル（raw_prices, raw_financials, raw_news, market_calendar など）が整っていることを前提とします。
- 設定は kabusys.config.settings から参照できます（例: settings.duckdb_path）。

---

## 設定管理の挙動
- パッケージ起動時に .env/.env.local を自動読み込みします（プロジェクトルートは .git または pyproject.toml で検出）。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します（テスト時に便利）。
- settings の主なプロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path（デフォルト data/kabusys.duckdb）
  - sqlite_path（デフォルト data/monitoring.db）
  - env（development | paper_trading | live）、log_level

---

## ディレクトリ構成（主要ファイル）
リポジトリ内の主要なモジュールとその概要:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news を再エクスポート)
    - news_nlp.py              — ニュースを集約して OpenAI でセンチメント評価、ai_scores へ保存
    - regime_detector.py       — マクロセンチメント + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult のエクスポート
    - jquants_client.py        — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py        — RSS 取得・前処理・保存補助
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - stats.py                 — zscore_normalize 等の汎用統計ユーティリティ
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                 — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py       — momentum/value/volatility ファクター計算
    - feature_exploration.py   — 将来リターン, IC, summary, rank 等

（上記以外にも strategy / execution / monitoring 等のサブパッケージが想定されていますが、今回提示されたコードの範囲では data / ai / research が主に実装されています。）

---

## 運用上の注意
- Look-ahead バイアス防止のため、モジュールの多くは date / target_date を明示的に受け取り、内部で datetime.today() を参照しない設計になっています。バックテスト時は適切な時刻管理に注意してください。
- OpenAI や J-Quants の API 呼び出しにはレートや課金が伴います。テスト時は小さなサンプルやモックを使用してください（各モジュールはテスト用に内部呼び出しをモックしやすく実装されています）。
- DuckDB に対する executemany の空リストはバージョン差で問題になることがあるため、モジュール側でガードされています。DB スキーマの初期化やマイグレーションは慎重に行ってください。

---

もし README に追加したい具体的なサンプル（例: docker-compose, CI 実行例、より詳細な .env.example、ユースケース別のワークフロー等）があれば教えてください。必要に応じて追記します。