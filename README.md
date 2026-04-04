# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（LLM連携）、ファクター計算、監査ログ、J-Quants / kabu API クライアントなど、取引システムに必要な主要処理のユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API を用いた市場データ（株価・財務・上場情報・カレンダー）の差分ETL
- RSS ニュース収集と OpenAI（gpt-4o-mini）を使った記事/銘柄単位のセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター（モメンタム / バリュー / ボラティリティ 等）の計算と研究支援ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ初期化
- kabu ステーション等との実行/監視周りの設定管理

設計上の留意点として、バックテストや学習時のルックアヘッドバイアス回避（外部の現在日時参照を避ける、ETL 時刻を記録する等）や、API 呼び出しの冗長対策（リトライ・バックオフ・レートリミット）に力を入れています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（差分・ページネーション対応）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - calendar_management: JPX カレンダー管理・営業日判定
  - news_collector: RSS 収集 → raw_news 保存（SSRF/トラッキング除去対策あり）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを使った銘柄別 ai_score 生成（OpenAI）
  - regime_detector.score_regime: ETF(1321) MA とマクロニュースを合成した市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン算出・IC計算・統計サマリ等
- config
  - 自動 .env ロード（プロジェクトルート探索）と Settings API（settings）

---

## 前提条件 / 必要環境

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (openai v1 互換 API を想定)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS 取得）
- 環境変数または .env に認証情報を設定すること

※ 本リポジトリには requirements.txt は含まれていません。実行環境に応じて上記パッケージをインストールしてください。

---

## 環境変数 / 設定

パッケージは .env / .env.local を自動でプロジェクトルートから読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須・代表的な環境変数は以下です。

必須（利用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL で必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必須）
- KABU_API_PASSWORD — kabu API パスワード（発注実装がある場合）

任意:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視パス
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

Settings API 例:
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（開発用）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール（例）
   pip install duckdb openai defusedxml
   またはプロジェクトに requirements.txt があれば pip install -r requirements.txt
4. ローカル開発としてインストール（任意）
   pip install -e .
5. .env をプロジェクトルートに作成（.env.example を参考に必要なキーを設定）

.env 例（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=hogehoge
DUCKDB_PATH=data/kabusys.duckdb
```

自動 .env ロードを無効化する場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから利用する最小例です。DuckDB はデフォルトでファイルを作成します。

1) DuckDB 接続を作成して ETL を実行（日次ETL）
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを計算して ai_scores に書き込む
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定を実行（market_regime テーブルへ書き込み）
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査用 DuckDB スキーマ初期化
```py
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続に対して:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(existing_conn)
```

5) ファクター計算（例: モメンタム）
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date": date, "code":"XXXX", "mom_1m":..., ...}, ...]
```

注意点:
- OpenAI 呼び出しは API エラー時にフェイルセーフで 0.0 を返したりスキップします。テスト時はモック（unittest.mock.patch）して _call_openai_api を差し替えることが推奨されています。
- ETL / 保存は DuckDB の ON CONFLICT DO UPDATE を使い冪等化されています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数/Settings 管理、.env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py          — ニュース NLP / OpenAI 呼び出し、score_news
  - regime_detector.py   — 市場レジーム判定、score_regime
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント、fetch/save 用関数
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult の再エクスポート
  - news_collector.py    — RSS 収集、前処理、raw_news 保存
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - quality.py           — データ品質チェック
  - stats.py             — 統計ユーティリティ（zscore_normalize）
  - audit.py             — 監査ログの DDL / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py   — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（上記は本リポジトリに含まれる主なモジュールの一覧です）

---

## 開発メモ / 運用上の注意

- OpenAI API 呼び出しは JSON Mode を用いて厳密な JSON 応答を期待する設計です。レスポンスパース失敗時はログを出してスコアを 0.0（またはスキップ）します。
- テストではネットワークや外部 API をモックし、_call_openai_api 等の内部呼び出しを差し替えることが想定されています。
- jquants_client は内部でレートリミッタと 401 自動リフレッシュ、リトライ処理を持っています。頻繁な API 呼び出しについては注意してください（デフォルト 120 req/min）。
- DuckDB に対する executemany の空リストバインドの制約（バージョンによって挙動が違う）を踏まえた実装が行われています。DuckDB のバージョンに依存する挙動には注意してください。
- settings.env の検証: KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL は検証があります。誤った値を入れると例外になります。

---

## 貢献 / ライセンス

リポジトリの方針に従ってプルリクエストやイシューで貢献してください。ライセンス情報はこの README には含まれていません。使用・配布の前にライセンスを確認してください。

---

不明点や追加で README に含めたい利用例（デプロイ手順、Dockerfile、CI 設定など）があれば指示してください。必要に応じてサンプルスクリプトや .env.example を作成します。