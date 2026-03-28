# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買（監査・発注トレーサビリティ）を想定した Python モジュール群です。J-Quants や RSS、kabu ステーション、OpenAI（LLM）を組み合わせ、データ ETL、品質チェック、ニュースセンチメント、ファクター算出、監査ログなどの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない等）
- DuckDB を用いたローカル DB 保存と冪等（ON CONFLICT）設計
- 外部 API 呼び出しはレート制御・リトライ・フェイルセーフを組み込む
- モジュール単位でテストしやすい分離設計（API 呼び出しの差し替えが容易）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（jquants_client, pipeline）
  - ETL の結果集約（ETLResult）と品質チェック（quality）
  - ニュース収集（RSS）の安全な取得・前処理・保存（news_collector）
  - 市場カレンダー管理・営業日ロジック（calendar_management）
- AI / NLP
  - ニュース記事を LLM でセンチメント化して ai_scores に保存（ai.news_nlp.score_news）
  - ETF（1321）の MA とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ（Research）
  - Momentum / Volatility / Value 等のファクター算出（research.factor_research）
  - 将来リターン計算、IC、統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査・トレーサビリティ
  - signal → order_request → execution の監査テーブル定義と初期化（data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数を自動読み込み（config）
  - 必須設定チェック API（settings オブジェクト）

---

## 必要条件（例）

- Python 3.9+
- duckdb
- openai
- defusedxml
- （その他、プロジェクトの requirements.txt に記載されるライブラリ）

例（仮）:
pip install duckdb openai defusedxml

（実際はプロジェクトの requirements.txt / poetry / pyproject.toml に従ってください）

---

## 環境変数 / 設定

config.Settings から主に以下の環境変数を参照します（必須は _require によるエラー）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
（OpenAI 用は関数引数で API キーを渡すか環境変数 OPENAI_API_KEY を使用）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live (デフォルト development)
- LOG_LEVEL: DEBUG/INFO/... (デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

.env の読み込み優先:
OS 環境変数 > .env.local > .env

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピーする
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/Mac) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt が無ければ、duckdb, openai, defusedxml 等を個別にインストール）
4. プロジェクトルートに .env（または .env.local）を作成し必須環境変数を設定
5. DuckDB / 監査 DB の準備（必要に応じて）

---

## 使い方（主要な API と例）

以下はいくつかの主要ユースケース例です。実行は Python スクリプトや REPL から行えます。

基本的な DB 接続（DuckDB）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

監査 DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn: duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント（LLM）によるスコアリング:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written ai_scores: {written}")
```

市場レジーム判定（MA + マクロニュース LLM）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

研究用関数の例（ファクター計算）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))

# 例: 特定カラムを Z スコア正規化
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- LLM 呼び出し（news_nlp / regime_detector）は OpenAI の API を利用します。API キーは引数または環境変数 OPENAI_API_KEY を使用してください。
- jquants_client は J-Quants のトークン（JQUANTS_REFRESH_TOKEN）を用いて id_token を取得します。
- ETL / API 呼び出しにはレート制御・リトライ・フェイルセーフが組み込まれていますが、実運用時は十分な監視を設けてください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py                 -- パッケージ初期化（version 等）
- config.py                   -- 環境変数 / .env 自動読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py               -- ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py        -- 市場レジーム判定（ETF MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py         -- J-Quants API クライアント / 保存関数
  - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
  - etl.py                    -- ETLResult の再エクスポート
  - news_collector.py         -- RSS フィード取得・前処理・保存
  - calendar_management.py    -- market_calendar と営業日ロジック
  - quality.py                -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py                  -- zscore_normalize 等の統計ユーティリティ
  - audit.py                  -- 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py        -- Momentum / Volatility / Value 等
  - feature_exploration.py    -- 将来リターン / IC / 統計サマリー

その他:
- data/                      -- デフォルトの DB 保存先（settings.duckdb_path のデフォルト）
- .env, .env.local            -- 環境変数（プロジェクトルートに置く）

---

## 設計上の注意 / 補足

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から探索して行います。テストや特殊な環境で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース操作は冪等（ON CONFLICT）を基本とし、部分失敗時に既存データを不必要に消さない設計になっています。
- LLM 領域はリトライ（指数バックオフ）や誤ったレスポンスのフォールバック（0.0）等のフェイルセーフを実装していますが、商用利用時は利用規約・コスト・レイテンシを考慮してください。
- DuckDB を使うためデータ量が増えるとローカルのディスク IO を監視する必要があります。

---

この README はコードベースに含まれる docstring / コメントをベースに要点をまとめたものです。実際の利用にあたっては、各モジュールの docstring を参照し、環境変数や API トークンの取り扱いに注意してください。質問や追加のサンプルが必要であれば教えてください。