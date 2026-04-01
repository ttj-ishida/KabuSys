# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ／発注トレースなどの機能を提供します。

---

## プロジェクト概要

KabuSys は下記を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（ETL）
- ニュース収集・前処理と OpenAI を用いた銘柄センチメント算出（ニュースNLP）
- マクロニュースと ETF の移動平均乖離を組み合わせた市場レジーム判定（regime_detector）
- 研究用のファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- ニュース RSS 取得時の SSRF 対策、前処理、安全な保存処理

設計方針として「ルックアヘッドバイアス防止」「冪等性」「外部APIのレート制御」「フェイルセーフ（API失敗時の継続）」を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（株価 / 財務 / マーケットカレンダー / 上場銘柄一覧）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- data.pipeline
  - 日次 ETL 実行（calendar / prices / financials）と品質チェック（quality）
  - ETLResult による集約結果
- data.quality
  - 欠損、スパイク、重複、日付不整合の検出
- data.news_collector
  - RSS 取得（SSRF 対策）、テキスト前処理、raw_news への保存ロジック
- ai.news_nlp
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（銘柄単位）
- ai.regime_detector
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- research.*
  - ファクター計算（momentum/value/volatility）や将来リターン計算、IC 計算、統計サマリー
- data.audit
  - 監査ログ用テーブル定義・初期化（signal_events / order_requests / executions）

---

## 前提 / 要件

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由の外部 API（J-Quants、OpenAI、RSS ソース）へのアクセス

（実プロジェクトでは requirements.txt を用意してください。例: `pip install duckdb openai defusedxml`）

---

## 環境変数（主なもの）

.env ファイルまたは実行環境で下記を設定してください。config.Settings により自動で読み込まれます（プロジェクトルートに .env / .env.local がある場合）。テスト時など自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注などを使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合
- OPENAI_API_KEY — OpenAI 呼び出しを行う場合（score_news/score_regime で使用）

任意（デフォルト値あり）:
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成して上記の値を設定

5. データベース保存用ディレクトリ作成（例）
   - mkdir -p data

---

## 使い方（簡単なコード例）

以下は各主要 API の利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続と日次 ETL 実行（データ取得・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 今日の ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニュースセンチメント（銘柄別）スコア算出
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対する前日15:00JST～当日08:30JST の記事でスコアリング
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None => 環境変数 OPENAI_API_KEY を使用
print("scored:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルにアクセスできる
```

- RSS フィード取得（ニュースコレクタ一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## よくある注意点

- Python バージョンは 3.10 以上を推奨（型表記に | 形式を使用）。
- OpenAI の呼び出しは外部 API のためレートやコストに注意してください。モデル・バッチサイズはコード内の定数で制御されています。
- J-Quants API はレート制限あり（コード内で制御）。認証トークンの取り扱いに注意してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- DuckDB executemany に空リストを渡すと問題になるバージョンがあるため本ライブラリでは空チェックを行っています。

---

## ディレクトリ構成（概要）

以下はパッケージ内の主要ファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（銘柄単位センチメント算出）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - news_collector.py — RSS 収集・前処理・保存ユーティリティ（SSRF 対策等）
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - monitoring/ (パッケージ公開リストに含まれる想定モジュール群)
  - strategy/, execution/ など（上位層の実装プレースホルダ／将来的な戦略・発注実装向け）

---

## 開発・テストに関するヒント

- OpenAI / J-Quants の API 呼び出しは外部接続を伴うため、ユニットテストではネットワーク呼び出しをモックすることを推奨します。コード内で多くの内部呼び出し関数（例: _call_openai_api, _urlopen）を差し替えやすく設計しています。
- DuckDB を用いることで高速な SQL 処理と単一ファイル DB を利用したローカル開発が可能です。テストでは `:memory:` を使ってインメモリ DB を用いることができます。
- ETL 実行結果は ETLResult.to_dict() で簡単にロギング・検査できます。

---

この README はコードベースから抽出した機能と設計方針を要約したものです。実運用やカスタム開発時は各モジュールの docstring・実装を参照してください。質問や追加のドキュメントが必要であれば教えてください。