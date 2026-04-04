# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、
データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムやリサーチ基盤で利用するためのモジュール群をまとめたライブラリです。主な目的は以下です。

- J-Quants API を利用した株価・財務・マーケットカレンダーの差分 ETL（DuckDB に保存）
- RSS ニュース収集と OpenAI を用いたニュースセンチメント/銘柄別 AI スコアリング
- ETF をベースにした市場レジーム判定（MA200 とマクロニュースの合成）
- ファクターの計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注・約定の監査ログスキーマ生成（監査トレース）
- 設定は環境変数 / .env ファイルから読み込み（自動ロード機構あり）

設計上の重点：
- ルックアヘッドバイアスに配慮（内部で date.today() 等を不用意に参照しない実装）
- DuckDB ベースのオフライン処理を想定（本番口座への直接アクセスはなし）
- OpenAI 呼び出しにはリトライやフォールバック（失敗時の安全なデフォルト）を組み込み

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、ページング、レート制御、保存関数）
  - ニュース収集（RSS -> raw_news、SSRF対策、URL正規化）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（audit schema / init_audit_db）
  - 汎用統計（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースを銘柄別に集約し OpenAI でスコアリング、ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321)の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（価格/財務のみ参照）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラスで環境変数を集中管理（自動 .env ロード機能）

---

## セットアップ手順

前提
- Python 3.10+（typing union 表現や match 表現を使用しているため近年の Python 推奨）
- DuckDB を利用
- OpenAI API を利用する場合は OpenAI の API キー（OPENAI_API_KEY）が必要
- J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要

1. リポジトリのクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール（代表的な依存）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

4. データディレクトリ作成（設定に応じて）
   ```
   mkdir -p data
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。
   - 必要な主要環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - その他オプション:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

6. 自動 .env 読み込みの挙動
   - 自動ロード順: OS 環境変数 > .env.local（上書き） > .env
   - プロジェクトルートの検出は .git または pyproject.toml を基準に行う
   - テスト時などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（基本例）

以下は主なユースケースのサンプルコード例です。適宜 conn は duckdb.connect の接続オブジェクトに置き換えてください。

1) DuckDB 接続を作成して ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーは env または api_key 引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算・前方リターン（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
```

5) 監査ログスキーマ初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログを操作できます
```

6) J-Quants クライアント直接利用（token を自動取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

# settings.jquants_refresh_token が設定されていれば id_token は内部で取得されます
records = fetch_daily_quotes(date_from=None, date_to=None)
```

注意点:
- OpenAI 呼び出しはモジュール単位でリトライやフォールバックを行います。API 料金やレートに注意してください。
- ETL や API 呼び出しはネットワークを伴うため、エラーハンドリングを適切に行ってください。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD：kabuステーション API のパスワード
- KABU_API_BASE_URL：kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：通知用途に任意
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（default data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等：監視プロセス設定
- KABUSYS_ENV：development | paper_trading | live（デフォルト development）
- LOG_LEVEL：DEBUG|INFO|WARNING|ERROR|CRITICAL

未設定の必須変数にアクセスすると Settings が ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュール構成（src/kabusys）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__pycache__... etc

（上記は主要モジュールのみ抜粋）

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しはユニットテストでモック可能です。モジュール内の _call_openai_api を patch してください（news_nlp/_call_openai_api, regime_detector/_call_openai_api）。
- DuckDB 接続は ":memory:" を指定してインメモリでテスト可能（例: duckdb.connect(":memory:")）。
- NewsCollector のネットワーク呼び出しもテスト時にはモックすべきです（HTTP/URLopen を差し替え）。

---

## ライセンス・貢献

（ここにライセンスや貢献方法を追記してください。）

---

README の内容はコードベースのドキュメントと整合するよう意図しています。追加で「使い方のサンプル」「.env.example」「CI / テスト実行方法」などを含めたい場合は、必要な項目を教えてください。