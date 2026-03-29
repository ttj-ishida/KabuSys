# KabuSys

KabuSys は日本株向けのデータ基盤・研究・自動売買のユーティリティ群を集めた Python パッケージです。  
DuckDB をデータレイクとして用い、J-Quants API / RSS / OpenAI（LLM）などと連携して、以下の用途をサポートします。

- データ ETL（株価・財務・マーケットカレンダー）
- ニュース収集・NLP（LLM による銘柄センチメント評価）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量解析（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化

以下はこのリポジトリに含まれる主要機能、セットアップ手順、利用例、ディレクトリ構成の説明です。

---

## 主な機能一覧

- data（データプラットフォーム）
  - J-Quants API クライアント（rate limiting / retry / token refresh）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・正規化・SSRF 対策・DB 保存向け）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査用テーブル・インデックスの作成）
  - 各種保存関数（DuckDB への冪等保存）
- ai（LLM を用いた NLP）
  - score_news: ニュースを銘柄別にまとめて LLM に投げ、ai_scores テーブルへ保存
  - score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを組合せて市場レジームを判定・保存
  - 両モジュールは OpenAI の JSON mode（gpt-4o-mini 等）を利用する設計
- research（研究用ユーティリティ）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- config
  - 環境変数の管理（.env / .env.local 自動ロード、必須チェック）
  - settings オブジェクト経由で設定値取得
- その他ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DuckDB 用監査 DB 初期化（init_audit_db）

---

## 必要条件（想定）

- Python 3.10 以上（構文で型合成演算子 `|` を使用）
- 主な依存パッケージ（プロジェクトの pyproject.toml / requirements.txt を参照してください）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

---

## 環境変数（主要）

必須（アプリケーションが要求する重要な変数）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants クライアントで使用）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime のデフォルト参照先）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知統合がある場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）:

- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットするとパッケージインポート時の .env 自動ロードを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD が未設定の場合、プロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を自動で読み込みます。

DB パスのデフォルト:

- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db

注意: settings オブジェクトは必須キーが未設定だと ValueError を投げます（例えば JQUANTS_REFRESH_TOKEN がない等）。

---

## セットアップ手順（ローカル開発向け）

1. Python とパッケージの準備
   - Python 3.10+ をインストール
   - 仮想環境を作る（推奨）
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （実際はプロジェクトの pyproject.toml / requirements.txt を利用してください）

3. リポジトリを編集可能モードでインストール（任意）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env ファイルを置くか、OS 環境変数として設定
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_kabu_pass
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB の初期スキーマ準備（監査ログ等）
   - Python で init_audit_db を呼ぶ（例は下記参照）

---

## 使い方（主要な API と例）

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続例

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 通常は target_date を省略すると今日が使われる
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの LLM スコアリング（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを引数で明示的に渡すことも可能
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB 初期化（監査テーブル作成）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 必要に応じてこの conn をアプリケーションの監査ログ用に使う
```

- RSS 取得（ニュースコレクタの低レベル関数）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url=url, source=source)
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI API を呼ぶため API キー（環境変数 OPENAI_API_KEY か引数）を必ず設定してください。
- run_daily_etl は J-Quants への認証に JQUANTS_REFRESH_TOKEN を利用します（settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント分析（LLM 呼び出し、ai_scores への書き込み）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/認証/リトライ/レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理・判定・更新ジョブ
    - news_collector.py — RSS 収集・前処理・SSRF 防御
    - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ定義 & 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ 等の計算関数
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/*.py ...（研究用ツール群）

この README は主要モジュールの概要をまとめたものです。各モジュールの関数・引数・返り値・振る舞いはソースコードの docstring（各関数上部のコメント）に詳細が記載されています。実際に組み込む場合はそれらの docstring を参照して下さい。

---

## 運用上の注意 / ベストプラクティス

- 環境の分離:
  - 開発 / paper_trading / live を KABUSYS_ENV で明示し、is_live 等で分岐して誤発注を防ぐこと。
- シークレット管理:
  - .env を使う場合は .env.local を .gitignore に入れて管理する。KABUSYS_DISABLE_AUTO_ENV_LOAD をテストで利用して自動ロードを抑制可能。
- Look-ahead バイアス対策:
  - 各モジュールは基本的に date 引数を受け取り、datetime.today() を直接参照しない設計になっています。バックテスト時は target_date を明示的に指定してください。
- OpenAI 呼び出し:
  - API レートや呼び出し失敗に備えて retry/backoff が組み込まれていますが、使用量に注意して下さい。
- DuckDB:
  - executemany を使う箇所で空リストを渡すとエラーになる点に注意（コード内でチェック済み）。

---

もし README の追加情報（例: pyproject.toml の内容、実運用での cron / Airflow の例、Slack 通知実装の詳細等）が必要であれば、目的に応じてサンプルやテンプレートを追記します。必要な情報を教えてください。