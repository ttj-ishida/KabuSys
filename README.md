# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からの市場データ取得 / 保存 / 品質チェック）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレース）、リサーチ用ファクター計算などの機能を提供します。

主に DuckDB を内部データ格納に用い、J-Quants / OpenAI / RSS など外部データソースを統合して運用バッチや研究ワークフローを支援します。

---

## 主な機能

- データ取得・ETL
  - J-Quants からの株価日足 / 財務データ / マーケットカレンダーの差分取得（ページネーション対応）
  - 差分保存（DuckDB、ON CONFLICT DO UPDATE による冪等化）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）
- ニュース収集 & 前処理
  - RSS フィード取得（SSRF 対策・gzip 上限）と raw_news 保存用ユーティリティ
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - LLM API 呼び出しに対するリトライ / バックオフ / レスポンス検証
- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義、初期化ユーティリティ（init_audit_schema / init_audit_db）
- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（必要であれば無効化可能）

---

## 要件

- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）

（実際の requirements.txt はプロジェクトの配布に従ってください。上記は主要依存の概観です。）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
   - 例: git clone ... && cd kabusys

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例:
     pip install duckdb openai defusedxml

   ※ 実運用では pip の requirements.txt を用意してインストールしてください。

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます（kabusys.config の自動ロード）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. `.env` に最低限必要な値を設定
   - 必須環境変数（このプロジェクトで直接参照している代表例）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime のデフォルト）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知利用時
     - KABU_API_PASSWORD      — kabuステーション API を使う場合
   - DB のパス（任意、デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要ユースケース例）

以下は簡単な Python スニペット例です。適宜ログ設定や例外処理を追加してください。

- DuckDB 接続と日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（AI）を実行して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定と書き込み
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
status = score_regime(conn, target_date=date(2026, 3, 20))
print("status:", status)
```

- 監査ログ用 DuckDB の初期化（専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB も可能
conn = init_audit_db("data/kabusys_audit.duckdb")
# 以降 conn に対して発注/シグナル監査ログを書けます
```

- RSS フェッチ単体（ニュース収集ロジックの呼び出し例）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- リサーチ（ファクター計算）例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- 各関数は「ルックアヘッドバイアス」対策として内部で date を明示的に参照し、現在時刻の直接参照を避ける設計になっています（バックテストでの安全性向上）。

---

## 環境変数の自動読み込み挙動

- 起動時に `.git` または `pyproject.toml` を基準にプロジェクトルートを探索し、以下の順で `.env` をロードします:
  1. OS 環境変数（既存のもの）
  2. .env（上書きしない）
  3. .env.local（上書きする）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。
- 必須の環境変数を参照するプロパティ（Settings クラス）は設定されていないと ValueError を送出します。

---

## ディレクトリ構成

プロジェクトの主要ソースは src/kabusys 配下にあります。主要ファイル・モジュールは次の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & DuckDB 保存ユーティリティ
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の公開
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py             — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py   — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
  - monitoring/, strategy/, execution/, ・・・（他サブパッケージが想定される）

（上はコードベースの抜粋で、実際のツリーは配布物に従ってください。）

---

## 開発向けの注意事項

- DuckDB の executemany は古いバージョンで空リストを受け付けない実装上の制約に対処するため、空チェックが各所に存在します。
- OpenAI 呼び出し部分はリトライ・JSON 検証・スロットリング設計を備えています。ユニットテストでは内部の _call_openai_api をモックして挙動を検証してください。
- news_collector は SSRF 対策（ホストのプライベート IP 判定、リダイレクト検査）や XML 怪しさ対策（defusedxml）を実装しています。

---

## ライセンス・貢献

この README はコードベースの説明目的のサマリです。実際のライセンスやコントリビュートガイドラインはレポジトリのルート（LICENSE, CONTRIBUTING.md 等）を参照してください。

---

必要であれば、README にインストール / CI / 実運用のデプロイ手順 (systemd / cron / Airflow / Kubernetes など) や `.env.example` のテンプレートを追加します。どの情報を追記しますか？