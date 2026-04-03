# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースNLP（OpenAI）・市場レジーム判定・監査ログ（約定トレース）など、運用に必要なユーティリティを含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- 要求環境 / 依存ライブラリ
- 環境変数
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本市場向けに設計されたデータパイプライン・リサーチ・AI 支援の共通ライブラリです。  
主に次の領域をカバーします。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）
- DuckDB ベースのデータ保存・ETL（差分取得・バックフィル・冪等保存）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）と前処理、LLM によるニュースセンチメント付与
- 市場レジーム判定（ETF MA とマクロニュースを組み合わせたスコア）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- リサーチ用ファクター計算・前方リターン計算・IC 計算など

設計上、ルックアヘッドバイアス回避、冪等性、堅牢なエラー処理（リトライ・フォールバック）を重視しています。

---

## 主な機能（機能一覧）

- data/
  - jquants_client: J-Quants からの取得・保存（fetch / save）・認証・レート制御
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（prices/financials/calendar）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - news_collector: RSS 取得・前処理・raw_news への保存支援
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログテーブル初期化・監査 DB ヘルパー
  - stats: z-score 正規化など統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを LLM に投げ銘柄毎にセンチメントを生成し ai_scores へ保存
  - regime_detector.score_regime: ETF(ma200) とマクロニュースの LLM スコアを組合せて market_regime に書込
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: forward returns, IC, factor summary, rank
- config:
  - Settings: 環境変数読み出し、.env 自動読み込み（プロジェクトルートの .env / .env.local）

---

## 要求環境 / 依存ライブラリ

- Python 3.10+（型アノテーションに union 型などを使用）
- 必須（コード参照）:
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- 標準ライブラリで HTTP/urllib を利用（requests は必須ではありませんが好みに応じて導入可）

実際のプロジェクトでは requirements.txt / pyproject.toml に依存を定義してください。

---

## 環境変数

config.Settings 経由で参照される主な環境変数は以下です（大文字）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (推奨) — OpenAI API キー（ai モジュールで未指定時に参照）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視・プロセス管理
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 に設定）

README と一緒に .env.example を用意しておくと便利です。.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...
2. 仮想環境作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトで pyproject.toml / requirements.txt があればそれを使用）
4. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参考）
   - 必須: JQUANTS_REFRESH_TOKEN
   - OpenAI を使う場合: OPENAI_API_KEY を設定
5. DuckDB 初期化（監査 DB を別 DB として準備する場合）
   - Python から利用例: from kabusys.data.audit import init_audit_db; conn = init_audit_db("data/audit.duckdb")
   - または既存の duckdb.Connection に対して init_audit_schema を実行
6. （任意）.env の自動読み込みを無効化したい場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（主要 API の例）

以下はライブラリをインポートして使うときの典型的な例です（簡略化）。

- ETL（日次パイプライン）を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を取得して ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key=None で OK
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written {written} codes")
```

- 市場レジーム判定を行う

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（スキーマ）を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- カレンダー関連ユーティリティ

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS フェッチ（ニュース収集）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しは rate/コストがかかります。テスト時はモック（unittest.mock.patch）することを推奨します。
- API キー未設定時、ai モジュールは ValueError を投げます（api_key 引数で注入可能）。

---

## 典型的なワークフロー（運用例）

1. 毎朝 / Cron で run_daily_etl を実行し DuckDB を更新
2. raw_news を定期収集してニュースを蓄積
3. score_news を実行して各銘柄に ai_score を付与
4. score_regime を実行して市場レジームを算出
5. research モジュールでファクター計算・シグナル生成
6. 生成シグナルは監査ログ（order_requests / signal_events）へ保存してから発注処理へ渡す

---

## ディレクトリ構成

（主なファイル・モジュール一覧、src 配下）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 他）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py  — forward returns, IC, summary, rank
  - ai/、research/ は研究・分析用の機能を提供

---

## テスト・開発時の注意点

- OpenAI 呼び出し（_call_openai_api）はユニットテストでモック可能（各モジュールで patch する箇所が想定されています）。
- J-Quants の HTTP 呼び出しは内部でレート制御とリトライを行いますが、テストでは fetch_* をモックして擬似レスポンスを返すことを推奨します。
- DuckDB の executemany はバージョン依存の挙動（空リスト不可など）があるため、コード中で注意されている箇所があります。実運用では DuckDB のバージョンを固定してください。

---

## 補足

- ここに示した README はコードベースの主要機能を紹介するための要約です。実際の導入・運用では .env.example、pyproject.toml / requirements.txt、運用ドキュメント（デプロイ・監視手順）を別途整備してください。
- 質問や補足説明が必要であれば、どの機能・どのファイルについて知りたいか教えてください。README を特定の使用例や運用手順に合わせて拡張します。