# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データの ETL、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログスキーマなどを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() を勝手に参照しない、API 呼び出しは明示的キー指定）
- DuckDB を中心としたローカルデータ格納（冪等保存）
- OpenAI / J-Quants API 呼び出しはリトライ・レート制御・フォールバックあり
- ETL / 品質チェックを通じてデータ信頼性を担保

---

## 機能一覧
- データ ETL（J-Quants からの株価・財務・カレンダー取得）
  - 差分取得、バックフィル、保存（冪等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策）
- ニュース NLP（OpenAI による銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- 監査ログ（signal / order_request / execution の監査スキーマ初期化）
- J-Quants クライアント（認証 / ページネーション / レート制御 / 保存ユーティリティ）
- 設定管理（.env 自動読み込み、環境別設定）

---

## 動作環境 / 依存
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging 等）

requirements.txt を用意している場合はそれを使ってインストールしてください。

---

## セットアップ手順（クイックスタート）
1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -e .  または  pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルートの `.env` / `.env.local` に必要な環境変数を設定します（下記参照）。
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）から自動で .env を読み込みます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

推奨の必須環境変数（例）
- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      … kabu API のパスワード（必須）
- OPENAI_API_KEY         … OpenAI API キー（news_nlp/regime_detector 用。関数引数で渡すことも可）
- その他（任意 / デフォルトあり）:
  - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, KABUSYS_ENV 等

例（.env）
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な例）

- DuckDB 接続を作って日次 ETL を実行する例

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日が使われます（ただし内部で look-ahead を避けた処理あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースをスコアして ai_scores に保存する（OpenAI キーは環境変数または引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

- 市場レジームスコアを計算して保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn を使って order/signals/executions を記録できます
```

- 設定にアクセスする

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

---

## API / メイン公開関数（抜粋）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.ETLResult
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(db_path)
- kabusys.data.jquants_client.* （fetch / save / get_id_token 等）
- kabusys.research.* （calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.stats.zscore_normalize

多くの関数は DuckDB の接続オブジェクトを受け取り、SQL と Python を組み合わせて結果を返します。OpenAI を使う処理は api_key 引数で上書き可能です。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数の自動読み込み・設定ラッパー（settings）
- ai/
  - news_nlp.py        … ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py … 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - jquants_client.py  … J-Quants API クライアント（取得・保存）
  - pipeline.py        … ETL パイプライン（run_daily_etl 等）
  - quality.py         … データ品質チェック
  - news_collector.py  … RSS 収集・前処理・保存ロジック
  - etl.py             … ETLResult 再エクスポート
  - calendar_management.py … 市場カレンダー管理（営業日判定 etc.）
  - stats.py           … 汎用統計ユーティリティ（zscore_normalize）
  - audit.py           … 監査ログスキーマ初期化ユーティリティ
- research/
  - factor_research.py … ファクター計算（momentum/value/volatility）
  - feature_exploration.py … 将来リターン / IC / 統計サマリー等
- ai/__init__.py, research/__init__.py などで主要 API を再公開

---

## 設計上の注意点 / 運用メモ
- API キーは環境変数で設定するのが推奨（.env を使用）。OpenAI を使う処理は api_key 引数で上書き可能。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CI/テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API レート制限（120 req/min）は jquants_client._RateLimiter により制御されます。
- ETL / 保存処理は基本的に冪等（ON CONFLICT DO UPDATE）です。ETLResult や quality.checks で結果を確認してから運用判断してください。
- OpenAI 呼び出しはリトライやパース失敗時にフェイルセーフで 0.0 にフォールバックするなど堅牢化されていますが、トークンや課金の取り扱いは運用側で注意してください。

---

必要があれば README にサンプル .env.example、cron での定期実行例やデプロイ手順（systemd / Dockerfile）などを追加できます。どの情報を優先して追記しますか？