# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買補助ライブラリ。  
価格・財務・ニュースの ETL、データ品質チェック、ニュースの LLM ベースセンチメント、マーケットレジーム判定、監査ログ（トレーサビリティ）などを提供します。

主に DuckDB をデータレイヤーに用い、J-Quants API / RSS / OpenAI を組み合わせて市場データの取得・前処理・特徴量生成までをカバーします。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API を使った株価・財務・カレンダーの差分 ETL（DuckDB 保存、冪等）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ETF（1321）200日移動平均などを使った市場レジーム判定
- 研究用途のファクター生成・統計ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の注意:
- ルックアヘッドバイアスを避ける実装方針（日時の取り扱いに注意）
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- DuckDB に対する保存は可能な限り冪等性を担保（ON CONFLICT 等）

---

## 機能一覧

主要機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）と環境変数ラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / トークン管理 / レート制限）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存補助
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティ
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースの銘柄別センチメントを生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュース（LLM）を組み合わせた市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt / pyproject.toml に記載してください）

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージ開発中であれば:
# pip install -e .
```

環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込みます（.git か pyproject.toml を基準にルートを探索）。
- 自動読み込みを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知に使用
- SLACK_CHANNEL_ID: Slack 通知先チャンネル
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）

設定の例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（簡易サンプル）

基本的な DB 接続と ETL 実行例:

```py
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# デフォルトの DuckDB パスは settings.duckdb_path
conn = duckdb.connect(str(settings.duckdb_path))

# 日次ETL を実行（target_date 省略で今日）
result = run_daily_etl(conn)

print(result.to_dict())
```

ニューススコアリング（OpenAI によるセンチメント）:

```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数に渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

市場レジーム判定:

```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# api_key 省略時は OPENAI_API_KEY を参照
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ DB 初期化:

```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は監査ログテーブルが作成された DuckDB 接続
```

research の例（ファクター計算）:

```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

注意点:
- OpenAI 呼び出しは API レート・費用が発生します。API キーを安全に管理してください。
- run_daily_etl などはネットワーク呼び出しを行うため、エラーハンドリングを適切に行ってください。

---

## 環境変数（Settings）

kabusys.config.Settings によってラップされています。主なプロパティ:

- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development / paper_trading / live。デフォルト development）
- log_level: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

.env ファイル読み込みの挙動:
- プロジェクトルートを .git または pyproject.toml で検出
- 読み込み順: OS 環境変数（優先） > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みをスキップ

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys）:

- __init__.py
- config.py
  - 環境変数読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py        → ニュースセンチメント（銘柄別）と calc_news_window
  - regime_detector.py → ETF MA とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  → J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline.py        → ETL パイプライン（run_daily_etl 等）
  - etl.py             → ETLResult の再エクスポート
  - calendar_management.py → マーケットカレンダー管理・営業日判定
  - news_collector.py  → RSS 取得・前処理
  - quality.py         → データ品質チェック（QualityIssue）
  - stats.py           → zscore_normalize 等
  - audit.py           → 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py → calc_momentum / calc_value / calc_volatility
  - feature_exploration.py → calc_forward_returns / calc_ic / factor_summary / rank

（上記以外に strategy / execution / monitoring 等のパッケージが示唆されていますが、今回のコードベースには主に data / ai / research が含まれています）

---

その他の注意
- DuckDB に保存するテーブルスキーマは各モジュールの実装に依存します。既存スキーマがない場合は ETL / init 関数を用いて初期化してください。
- OpenAI API 呼び出しはレスポンスのフォーマット検証を行い、失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計になっていますが、ログ出力で失敗理由を必ず確認してください。
- 監査ログ（audit）ではタイムスタンプを UTC に固定します（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

お問い合わせ・貢献
- バグ報告・機能提案は issue を立ててください。
- コントリビューションは Pull Request を歓迎します。README を適宜更新してください。

以上。