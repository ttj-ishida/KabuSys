# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDBベースのデータレイクを管理するETL、ニュースNLP・市場レジーム判定（OpenAI利用）、ファクター計算、品質チェック、監査ログ（発注/約定トレース）など、量的運用・研究用途に必要な主要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- 環境変数（主要）
- セットアップ手順
- 使い方（簡単なサンプル）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から日本株の株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事前処理、OpenAI を用いたニュースセンチメントスコアリング（銘柄別）
- ETF（1321）の移動平均乖離とマクロニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム/バリュー/ボラティリティ等）の計算・探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用スキーマ初期化ユーティリティ

設計上の共通方針として、バックテストに有害なルックアヘッドバイアスを避ける実装（日時の直接参照回避・DBクエリ条件の工夫）や、外部API失敗時のフェイルセーフ（スコアを中立にフォールバック）などが盛り込まれています。

---

## 機能一覧

主な機能（モジュール別）：

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定プロパティ（J-Quants トークン、OpenAI/Slack キー、DBパス、環境モード等）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・レート制御・DuckDB への保存関数
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 収集・前処理（SSRF/サイズ制限対策、URL 正規化）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定のユーティリティ
  - audit: 監査ログ（テーブル定義・初期化、init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを生成して ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime に書き込む
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- 監査・実行・モニタリング用の基盤（監査テーブル設計、インデックス、DDL）

---

## 前提・依存関係

最低限の推奨依存パッケージ（プロジェクトに requirements.txt がない場合は各自インストール）:

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリで多くを実装しているため、外部依存は最小限）

インストール例（venv を作った上で）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布があれば:
# pip install -e .
```

---

## 環境変数（主要）

.env または環境変数で指定します。プロジェクトルート（.git または pyproject.toml を含むディレクトリ）から自動的に `.env` → `.env.local` の順で読み込まれます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（ライブラリの一部機能で必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client が使用）
- SLACK_BOT_TOKEN : Slack 通知に使用する場合
- SLACK_CHANNEL_ID : Slack 通知チャンネル
- KABU_API_PASSWORD : kabuステーション API を使う場合

オプション／デフォルトあり:
- OPENAI_API_KEY : OpenAI API キー（ai.score_* 関数で省略時に参照）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)

注意: Settings クラスは必須鍵が見つからない場合に ValueError を送出します（呼び出し側で捕捉してください）。

---

## セットアップ手順

1. Python 環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # また必要に応じて他パッケージ（例: requests 等）を追加
   ```

3. プロジェクトルートに .env を作成（.env.example を参考に）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB / 監査DB 初期化（任意: 監査ログを使う場合）
   - 監査専用DBを初期化する例は下記「使い方」を参照

---

## 使い方（サンプル）

以下は代表的な利用例です。各操作は Python スクリプトやジョブとして実行してください。

- DuckDB に接続して日次 ETL を実行する（run_daily_etl）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ってニューススコアを算出（ai.news_nlp.score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていることを前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を実行（ai.regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DBを初期化する（監査用 DuckDB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn に対してアプリで発注ログ等を保存していく
```

- J-Quants の ID トークンを取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
print(token)
```

- RSS をフェッチ（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意: 上記はライブラリ API の呼び出し例です。実際には取得した記事やスコアを DB に保存する処理を組み合わせた上で運用することを想定しています。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要ファイル/モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント評価（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETL 結果型の公開
    - news_collector.py           — RSS 収集 / 前処理
    - quality.py                  — データ品質チェック
    - calendar_management.py      — 市場カレンダー管理（営業日判定等）
    - audit.py                    — 監査ログスキーマ初期化 / init_audit_db
    - stats.py                    — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py          — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      — calc_forward_returns / calc_ic / factor_summary / rank

（詳細はリポジトリの src/kabusys 配下を参照してください）

---

## 注意事項 / 設計ポリシー

- Look-ahead bias（先見性バイアス）を避ける実装が各所に施されています。target_date の扱いや DB クエリ条件に注意しており、datetime.today() を直接参照しない設計になっています。
- OpenAI / J-Quants 等の外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備えています。API キーが無い・エラー時は中立（0.0）で継続する処理が多く、呼び出し時に例外が上がるケースは限定的です（ただし、API キー未設定時は ValueError を送出する関数もあります）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探す）に依存します。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の INSERT 操作は冪等性を考慮して ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等で実装されています。
- ニュースの RSS 収集は SSRF 対策（ホストのプライベートIP拒否、リダイレクト検査）、受信サイズ制限、XML の安全パーシング（defusedxml）などを備えています。

---

必要であれば README に次の追加を行えます：
- 環境変数の .env.example（テンプレート）
- CI / デプロイ手順
- 具体的なジョブスケジューリング（cron/airflow）例
- テスト手順とモック方法（OpenAI / J-Quants のモック）

ご希望があれば上記のいずれかを付け加えた README を作成します。