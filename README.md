# KabuSys

日本株を対象とした自動売買／データパイプライン用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースNLP（OpenAI でのセンチメント）・市場レジーム判定・研究用ファクター計算・監査ログ（トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は、日本株のデータプラットフォームと自動売買ワークフローを支える Python モジュール群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いたローカルデータストアと冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と OpenAI を用いた銘柄別ニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースを合成）
- 研究用ファクター計算・統計ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計上の特徴：
- Look-ahead バイアス回避（日時参照は呼び出し側で与えられる target_date ベース）
- 冪等性（DB への保存は ON CONFLICT を利用）
- フェイルセーフ（外部 API 失敗時は部分的にフォールバックして継続）
- 明示的な品質チェックと監査ログ

---

## 主な機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- ニュース収集と NLP
  - fetch_rss / news 前処理（kabusys.data.news_collector）
  - news スコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - score_regime（kabusys.ai.regime_detector）: ETF 1321 の MA200 とマクロニュースを合成
- 研究用モジュール
  - ファクター計算（momentum / value / volatility）および特徴量解析（kabusys.research）
  - zscore_normalize（kabusys.data.stats）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - 環境変数・.env 自動読み込み / settings（kabusys.config）

---

## セットアップ手順

前提
- Python 3.10 以上

推奨パッケージ（例）
- duckdb
- openai
- defusedxml

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 他に必要な依存があれば追加してください
```

.env（環境変数）設定  
プロジェクトルートに `.env` として以下を設定してください（必要なもののみ）。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロード動作:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

データディレクトリを作成:
```bash
mkdir -p data
```

---

## 使い方（サンプル）

以下は代表的な Python API の使い方例です。DuckDB 接続は通常 `settings.duckdb_path` を利用します。

基本的な初期化
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースのスコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY をセット
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

市場レジーム判定（1321 MA200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # または ":memory:"
```

設定の読み方
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- OpenAI 呼び出しは API 料金が発生します。テスト時はモック推奨（モジュール内の _call_openai_api をパッチ可能）。
- 各処理は look-ahead を避けるため target_date を呼び出し側で与える設計です。内部で datetime.today() 等を直接参照しません。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

未設定で必須のものが参照されると `ValueError` が発生します（settings.propeties がチェックします）。

---

## ディレクトリ構成

下記は主なファイル・モジュールの一覧（ソースツリーの抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・.env 読み込み設定
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースセンチメント（OpenAI）
    - regime_detector.py       # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存ロジック
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - etl.py                   # ETLResult 再エクスポート
    - news_collector.py        # RSS 収集・前処理
    - calendar_management.py   # 市場カレンダー管理・営業日判定
    - quality.py               # データ品質チェック
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - audit.py                 # 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py       # momentum / value / volatility 等
    - feature_exploration.py   # forward returns / IC / summary / rank

各モジュールはドキュメント文字列で設計方針や使用法が記載されています。ソース内の docstring を参照してください。

---

## 補足・運用上の注意

- API レート制御や再試行ロジックが実装されていますが、環境に応じてパラメータ調整が必要な場合があります（例: RateLimit）。
- OpenAI キーや J-Quants トークンは秘匿情報です。CI/CD や運用環境ではシークレットストアを使用してください。
- DuckDB スキーマ（raw_prices / raw_financials / market_calendar / ai_scores / market_regime など）は ETL 実行前に適切に初期化されている必要があります（プロジェクト内に schema 初期化ユーティリティがある場合はそちらを利用してください）。
- テスト時は環境変数自動読み込みを無効化できます: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 参考

- ソース内の docstring に各関数の詳細・設計方針・例外挙動が書かれています。実装を拡張する際はそちらを第一に参照してください。

ご要望があれば、README にサンプル .env.example、スキーマ初期化手順、あるいは具体的なユースケース（バックテスト用データの準備、監査DB の運用、OpenAI モック方法など）を追加します。どの情報を優先して追記しますか？