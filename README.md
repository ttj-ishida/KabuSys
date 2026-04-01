# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（LLMを用いたセンチメント評価）、市場レジーム判定、監査ログ（トレーサビリティ）、リサーチ用ファクター計算などのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する共通コンポーネント群です。主に以下を提供します。

- J-Quants API と連携したデータ取得／保存（株価、財務、マーケットカレンダー等）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集・前処理・NLP スコアリング（OpenAI を利用した銘柄別センチメント）
- 市場レジーム判定（ETF とマクロニュースを組み合わせた判定）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化 等）
- 監査ログ（signal → order_request → execution のトレースを保持する DuckDB スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 市場カレンダー管理（JPX カレンダーの差分更新・営業日判定）

設計上、バックテストや運用で発生しがちな「ルックアヘッドバイアス」を避ける工夫（datetime.now()/today の安易な参照を避ける等）が随所に施されています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - DuckDB への冪等保存 (ON CONFLICT DO UPDATE)
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果表現: ETLResult
- データ品質チェック
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
  - QualityIssue 型による詳細レポート
- ニュース収集・NLP
  - RSS フィードの収集・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別センチメント score_news（gpt-4o-mini、JSON Mode）
- 市場レジーム判定
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成してレジーム判定
- リサーチ
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank
  - 統計ユーティリティ: zscore_normalize
- カレンダー管理
  - market_calendar の差分取得と夜間更新（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db：監査ログ用の DuckDB スキーマを初期化
  - signal_events / order_requests / executions テーブルとインデックス

---

## セットアップ手順

前提: Python 3.10+（型アノテーションに union | を使用しているため）を推奨します。

1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトは pyproject.toml を想定しています（パッケージ配布想定）。

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要依存パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合は主要依存を手動でインストールします:
     - pip install duckdb openai defusedxml
     - （必要に応じて他のパッケージを追加）

   - 開発インストール（パッケージ化されていれば）:
     - pip install -e .

4. 環境変数 / .env の設定
   - プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: （Slack 通知を使う場合）Bot トークン
     - SLACK_CHANNEL_ID: （Slack 通知を使う場合）チャンネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード（約定連携等）
     - OPENAI_API_KEY: OpenAI を利用する機能（news_nlp, regime_detector）で必要
   - その他のオプション:
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   - .env のフォーマットはシェル形式（export KEY=val も可）。config モジュールが詳しく解析します。

5. DuckDB ファイル用ディレクトリの作成（必要なら）
   - デフォルトは data/ 配下を使用するため、data/ を作成しておくと良いです:
     - mkdir -p data

---

## 使い方（主要な API と実行例）

※ 以下は簡単な例です。実運用ではログ設定や例外処理、トークン管理等を適切に行ってください。

- 設定の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのセンチメント（銘柄別）をスコアリング
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定（ETF 1321 をベース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査用 DB を別ファイルに作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を既存 conn に対して実行
```

- RSS フィードを取得する（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

- J-Quants から一覧情報を取得
```python
from kabusys.data.jquants_client import fetch_listed_info

listed = fetch_listed_info()
print(len(listed))
```

- 研究用ファクター計算の使い方（一例）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

---

## 推奨される環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP): OpenAI API キー
- KABU_API_PASSWORD (必須 for kabu 接続)
- KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意): 通知用
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV (任意): development / paper_trading / live
- LOG_LEVEL (任意): INFO（既定）など

自動で .env を読み込ませたくない時:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

プロジェクトは src パッケージ配下に配置されています。主な構成は次のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      # ニュースセンチメント（銘柄別）
    - regime_detector.py               # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント＋DuckDB保存
    - pipeline.py                      # ETL パイプライン / run_daily_etl 他
    - etl.py                           # ETLResult の再エクスポート
    - news_collector.py                # RSS 収集・前処理
    - calendar_management.py           # 市場カレンダー管理
    - quality.py                       # データ品質チェック
    - stats.py                         # 統計ユーティリティ（zscore_normalize）
    - audit.py                         # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               # momentum / value / volatility 等
    - feature_exploration.py           # forward returns / IC / summary / rank
  - ai, research, data モジュール群（上記）

各モジュールには詳細な docstring が付与されており、内部設計やエラーハンドリング方針、ルックアヘッドバイアス対策に関する注意点が記載されています。

---

## 注意点 / 運用上の留意事項

- OpenAI 呼び出しにはネットワークのエラーやレート制限があるため、各モジュールでリトライやフォールバック（失敗時に 0.0 を返す等）が実装されています。API キー管理に注意してください。
- J-Quants API はレート制限が設定されているため、jquants_client 内で固定間隔のレート制御と再試行ロジックを備えています。
- DuckDB の executemany に関するバージョン依存（空リストを渡せない等）を考慮し、一部箇所でガードが実装されています。
- ニュース収集は SSRF や XML 攻撃対策（SSRF 検査、defusedxml、受信バイト数制限など）を含みますが、ユーザ側でもフィード URL の管理やネットワークファイアウォール等を併用してください。
- 監査ログ（audit）スキーマは冪等で初期化可能です。運用時は常に created_at/updated_at を保ち、監査ログを削除しない設計が推奨されます。

---

## 参考・デバッグ

- ログレベルや環境（KABUSYS_ENV・LOG_LEVEL）を設定して詳細ログを確認してください。
- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env 自動読み込みを無効化できます（テストなどで便利です）。
- DuckDB の SQL を直接叩けばデータ中身を確認できます（例: SELECT * FROM raw_prices LIMIT 10）。

---

必要であれば README に実行スクリプト例（cron/timeserver 用）や .env.example のサンプル、依存パッケージの完全な一覧、ユニットテスト実行方法（pytest 等）を追加します。どの情報をさらに補足しますか？