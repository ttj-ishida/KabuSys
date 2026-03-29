# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集と NLP（OpenAI）、ファクター計算、監査ログなどを提供し、戦略実装・発注・モニタリングの基盤となることを目的としています。

Version: 0.1.0

---

## 概要

主な設計方針・特徴:
- DuckDB を用いた高速かつ軽量なオンディスク DB を想定したデータ層
- J-Quants API 経由で株価・財務・マーケットカレンダーを差分取得・保存
- RSS ベースのニュース収集と、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価
- ニュース/価格データを用いた市場レジーム判定（MA200 + マクロニュース）
- ETL/品質チェックでデータ健全性を確保（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）によるトレーサビリティ
- 研究用モジュール（ファクター計算、IC、将来リターン計算、正規化など）
- ルックアヘッドバイアスを避ける設計（内部で date.today() 等を直接参照しない点に配慮）

---

## 主な機能一覧

- 環境変数管理（自動 .env ロード・必須項目チェック）
- J-Quants クライアント
  - 株価日足 / 財務データ / 上場銘柄情報 / マーケットカレンダーの取得
  - レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理、news_symbols との紐付け
- OpenAI を用いたニュースセンチメント（news_nlp.score_news）と市場レジーム判定（regime_detector.score_regime）
- 研究（research）モジュール：モメンタム・バリュー・ボラティリティ等のファクター計算、IC / 統計サマリー
- 監査ログ初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

---

## 前提・依存ライブラリ（例）

本 README はコードベースから機能を要約したものです。実行には以下の主要パッケージが必要です（バージョンは適宜選択してください）。

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクト配布に requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存ライブラリをインストールする（上記参照）
3. 環境変数を設定する（.env をプロジェクトルートに置くと自動ロードされます）
   - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. DuckDB ファイルや監査DBを初期化する（必要に応じて）

推奨開発フロー（例）:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # または個別インストール
```

---

## 設定（.env / 環境変数）

プロジェクトはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（例: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に特定します。
- テスト時に自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼び出すサンプルです。実環境ではエラーハンドリングやログ設定を適切に行ってください。

- DuckDB 接続を作り、日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコア化して ai_scores テーブルへ書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print("written:", written)
```

- 市場レジーム判定を実行する:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("regime score saved:", res)
```

- 監査用 DuckDB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- RSS フィード取得（news_collector.fetch_rss）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

テスト・モックについて:
- OpenAI 呼び出しは内部で専用の `_call_openai_api` をラップしているため、unittest.mock.patch によりテスト時に差し替えやスタブ化が可能です（例: kabusys.ai.news_nlp._call_openai_api）。

---

## ディレクトリ構成

主要ファイル/モジュールの一覧（省略あり）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み・設定オブジェクト (settings)
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI 呼び出し、バッチ処理、レスポンス検証）
    - regime_detector.py  — MA200 と マクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - pipeline.py         — ETL パイプライン（run_daily_etl / 個別 ETL 実装）
    - etl.py              — ETLResult の公開エイリアス
    - news_collector.py   — RSS 収集・前処理・保存ロジック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - quality.py          — データ品質チェック群
    - stats.py            — 統計ユーティリティ（z-score 等）
    - audit.py            — 監査ログ用テーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク化
  - (将来的 / 別モジュール)
    - strategy/           — 戦略ロジック（エントリポイント等）
    - execution/          — 発注・ブローカー連携
    - monitoring/         — 監視・アラート

---

## 開発メモ / 設計上の注意

- Look-ahead バイアス対策として、ほとんどのモジュールは target_date を明示的に受け取り、内部で現在日時を直接参照しない実装になっています。
- API 呼び出しは可搬性とテスト性を考慮して抽象化されており、モック差し替えが容易です。
- DuckDB に対する executemany の空パラメータ回避など、実際のランタイム問題に対する互換性処理が散見されます。
- 監査ログは削除しない設計（トレーサビリティ優先）です。order_request_id を冪等キーとして使用します。

---

## ライセンス / コントリビュート

本リポジトリにライセンスファイルが含まれていない場合は、利用前にプロジェクトオーナーへ確認してください。  
コントリビュート方法や開発ルールは別途 CONTRIBUTING.md 等を作成してください。

---

この README はコードの現状から自動生成的に要約したものです。個々の関数や API の詳細な使い方はソースコード内の docstring を参照してください。質問や追加のドキュメント化（API リファレンス、チュートリアル、運用手順等）をご希望であれば知らせてください。