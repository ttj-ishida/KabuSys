# KabuSys

日本株自動売買プラットフォームのコアライブラリ群です。  
データ ETL、品質チェック、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）、J-Quants API クライアントなど、バックテスト／研究／本番運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの基盤ライブラリです。主な目的は次のとおりです。

- データ取得（J-Quants API）と DuckDB への差分保存（ETL）
- 市場カレンダーの管理（営業日判定・更新ジョブ）
- ニュース収集（RSS）と LLM によるセンチメントスコアリング
- 市場レジーム判定（テクニカル指標 + LLM）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）

設計上の特徴として、ルックアヘッドバイアス回避（日付の外部注入）、冪等性、フェイルセーフ（外部API失敗時は継続）を重視しています。

---

## 機能一覧

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- ニュース収集（RSS -> raw_news）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（score_news：OpenAI を用いた銘柄別センチメントスコア）
- 市場レジーム判定（score_regime：ETF MA とマクロニュース LLM の合成）
- 研究モジュール（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize）
- J-Quants API クライアント（トークン取得・ページネーション・保存関数）
- 監査テーブル初期化・監査 DB 作成（init_audit_schema / init_audit_db）
- 設定管理（環境変数・.env 自動読み込み、Settings オブジェクト）

---

## 前提 / 必要環境

- Python 3.10+
- 推奨パッケージ（主な依存）:
  - duckdb
  - openai
  - defusedxml

（必要に応じて他のユーティリティも追加される可能性があります）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 他に必要なパッケージがあれば追加してください
```

---

## 環境変数 / .env

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます（環境変数が優先されます）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（README 用サンプル）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルトあり）

# OpenAI (news_nlp / regime_detector 実行時に必要)
OPENAI_API_KEY=sk-...

# Slack (通知等に使用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

設定値は `from kabusys.config import settings` でアクセスできます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成して依存をインストール
3. `.env` をプロジェクトルートに作成して必要な環境変数を設定
4. DuckDB の初期スキーマ（監査ログ等）を必要に応じて初期化

監査 DB の初期化例:

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)  # transactional=True を渡すことも可
# conn は duckdb の接続オブジェクト
```

---

## 使い方（主要な例）

以下は簡単な Python スクリプト / REPL 例です。

- DuckDB 接続を作る（settings を利用）:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {n} symbols")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- ファクター計算（例: モメンタム）:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{'date':..., 'code':..., 'mom_1m':..., ...}, ...]
```

- データ品質チェックを個別に実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date=None は全件チェック
for i in issues:
    print(i)
```

- ニュース収集（RSS を取り込む）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意:
- OpenAI を使う機能は API キー（環境変数 OPENAI_API_KEY または関数引数）を必要とします。
- 自動実行系（ETL / news scoring / regime scoring）は外部 API を呼ぶため、実行前に環境変数とネットワーク設定を確認してください。
- テスト時は OpenAI 呼び出し／ネットワーク関数をモックすることを推奨します（コード内に差し替えポイントあり）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール構造（src/kabusys 以下）:

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ quality.py
│  ├─ stats.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  └─ audit.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/（上記に続く）
```

主要モジュールの役割:
- kabusys.config: 環境変数と .env のロード、アプリ設定オブジェクト（settings）
- kabusys.data.jquants_client: J-Quants API 呼び出し／保存ロジック
- kabusys.data.pipeline: 日次 ETL のエントリポイントと ETLResult
- kabusys.data.news_collector: RSS 収集・前処理（SSRF 対策等）
- kabusys.ai.news_nlp: 銘柄別ニュースセンチメントの LLM 評価
- kabusys.ai.regime_detector: マーケットレジーム判定（MA200 + マクロニュース）
- kabusys.research.*: ファクター計算・特徴量解析用ユーティリティ
- kabusys.data.audit: 監査ログ（シグナル → 発注 → 約定）スキーマと初期化

---

## テスト・開発時のヒント

- 自動 .env 読み込みはデフォルトで有効。ユニットテストや CI で .env の影響を排除したい場合は
  `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や J-Quants への呼び出しはリトライやフェイルセーフ実装がありますが、テストでは外部呼び出しをモックしてください（モジュール内の `_call_openai_api` 等を patch する設計）。
- DuckDB はローカルファイル（デフォルト data/kabusys.duckdb）に保存されます。テストでは `":memory:"` を使うと便利です。
- ロギングは各モジュールで logger を利用しています。`LOG_LEVEL` 環境変数でログレベルを調整できます。

---

## 免責・注意事項

- 本ライブラリは取引ロジック（実際のポジション管理や注文戦略）を提供するものではありません。実際の売買を行う際は十分な検証とリスク管理を行ってください。
- 外部 API キー（OpenAI / J-Quants / 証券会社等）は厳重に管理してください。
- 本ドキュメントはソースコードを元に作成しています。実際のリポジトリでは依存関係（requirements / pyproject）や追加ドキュメントを確認してください。

---

必要があれば、セットアップスクリプト、.env.example のテンプレート、または主要ワークフロー（ETL の定期実行、ニューススコアリングのバッチ化、監査 DB 運用手順など）の具体的なサンプルを追加で作成します。どの部分を詳しく知りたいか教えてください。