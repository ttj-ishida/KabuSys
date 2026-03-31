# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（LLM によるセンチメント）・市場レジーム判定・研究用ファクター計算・監査ログなど、アルゴ戦略のバックエンドを提供します。

この README はパッケージソース（src/kabusys）に基づく簡易ドキュメントです。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と自動読み込み
- 使い方（主要 API の例）
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python ライブラリです。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- ニュース記事を収集・前処理し、OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出して ai_scores に保存
- ETF（1321）を用いた市場レジーム判定（MA200 とマクロニュースを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と各種統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマ初期化ユーティリティ

設計上の重要点：
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を盲目的に参照しない設計（API 呼び出しは target_date を明示的に渡す）
- DuckDB を利用したローカル DB ベースでの ETL/解析
- OpenAI 呼び出しに対するリトライやフェイルセーフ（API 失敗時はスコア 0 として続行する等）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・正規化・保存ロジック）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄別ニュースセンチメント算出と ai_scores 書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — MA200 とマクロニュースを合成した market_regime 書き込み
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 等（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数管理（必須値の取得、.env 自動読み込みロジック）

---

## セットアップ手順

前提：
- Python 3.10 以上を推奨（型注釈に Union | を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

例: 仮想環境を使ったセットアップ

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトを editable インストールする場合）
   - pip install -e .

   ※ 実行環境に応じて他ライブラリが必要な場合があります（例: psycopg2 などは本コード内には含まれていません）。

3. 環境変数を設定（次節参照）

4. DuckDB ファイルやデータディレクトリを作成（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）

---

## 環境変数（.env）と自動読み込み

kabusys.config.Settings は環境変数から各種設定を取得します。重要な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（該当コードが利用する場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY — OpenAI 呼び出しに使われる（score_news / score_regime に渡せる）

自動 .env 読み込みの仕様：
- プロジェクトルートを .git または pyproject.toml の位置から探索して決定します（CWD に依存しない）。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## 使い方（主要 API の例）

以下は主要なユースケースの最小サンプルです。DuckDB 接続には duckdb.connect() を用います。

1) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントの計算（OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、api_key を直接渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

3) 市場レジーム判定（1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect('data/kabusys.duckdb')
momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

6) カレンダー関数の利用例
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect('data/kabusys.duckdb')
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- OpenAI 呼び出しにはネットワークと適切な API キーが必要です。API 呼び出しで失敗した場合、一部の処理はフェイルセーフ（0.0 スコア等）で継続する設計です。
- DuckDB に対する executemany 等は空リストを渡すとエラーになるバージョンの互換性考慮がなされています（コード内にチェックあり）。

---

## ディレクトリ構成（主要ファイル・概要）

（パッケージのルートは src/kabusys）

- __init__.py
  - パッケージのバージョンと公開サブモジュール: data, strategy, execution, monitoring（strategy 等の実装はこの抜粋に含まれていません）

- config.py
  - Settings クラス: 環境変数取得、.env 自動読み込みロジック、env/log_level 検証等

- ai/
  - __init__.py
    - score_news をエクスポート
  - news_nlp.py
    - calc_news_window, score_news: ニュース記事の集約・LLM 呼び出し・ai_scores 書き込み
  - regime_detector.py
    - score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込み

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* 関数、rate limiter、認証（get_id_token）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）と ETLResult データクラス
  - calendar_management.py
    - market_calendar 管理、営業日判定、calendar_update_job
  - news_collector.py
    - RSS 取得・前処理・記事 ID 正規化・SSRF 対策など
  - quality.py
    - データ品質チェックと QualityIssue 型
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログスキーマの DDL と初期化（init_audit_schema / init_audit_db）
  - etl.py
    - ETLResult の再エクスポート

- research/
  - __init__.py
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank

許可済み外部ライブラリ（主に実行に必要）
- duckdb
- openai
- defusedxml

---

## 実運用時の留意点

- API トークン管理は厳重に行ってください（.env をリポジトリに含めない等）。
- OpenAI のコストとレート制限、J-Quants のレート制限を考慮してバッチ設計を行ってください。
- DuckDB のファイルパスやバックアップ戦略を検討してください（監査ログは削除しない前提）。
- テスト時に .env 自動読込を無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本パッケージはバックテストと実取引の分離を想定しています（設定 KABUSYS_ENV 等を利用）。

---

必要であれば README に「環境変数の完全な一覧」「SQL スキーマの詳細」「サンプル ETL スケジューラ（cron / Airflow）設定」などを追加できます。どの追加情報が必要か教えてください。