# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
J-Quants / DuckDB を用いたデータ ETL、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注／約定トレーサビリティ）、研究（ファクター計算／特徴量探索）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム構築および研究に必要な以下の機能を提供する Python パッケージです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得（ETL）
- DuckDB を用いた永続化・集計処理
- ニュースの収集・前処理と OpenAI によるセンチメント評価（ニュースNLP）
- マクロ + テクニカルを用いた市場レジーム判定（regime detector）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 研究用モジュール（モメンタム/バリュー/ボラティリティ計算、将来リターン、IC、統計サマリ）
- マーケットカレンダー管理（営業日判定・更新ジョブ）
- ニュース RSS 収集（SSRF 対策、トラッキング除去、前処理）

設計上の特徴として、バックテストでのルックアヘッドバイアス回避や、API 呼び出しの堅牢なリトライ、冪等性の担保を重視しています。

---

## 主な機能一覧

- data.jquants_client: J-Quants API の取得・保存（fetch / save）、トークン自動リフレッシュ、レート制御
- data.pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.quality: データ品質チェック（missing_data, spike, duplicates, date_consistency, run_all_checks）
- data.news_collector: RSS 収集、前処理、raw_news への保存用ユーティリティ
- ai.news_nlp: ニュースをまとめて OpenAI に送り銘柄別スコアを ai_scores に保存（score_news）
- ai.regime_detector: ETF（1321）の MA200 乖離 + マクロニュースセンチメントを合成して market_regime を書き込む（score_regime）
- data.calendar_management: 営業日判定・next/prev/get_trading_days、calendar_update_job
- data.audit: 監査ログ DDL / init_audit_db / init_audit_schema
- research.*: ファクター計算（calc_momentum, calc_value, calc_volatility）や特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- data.stats: zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ

前提
- Python 3.10 以上（型ヒントに PEP 604 表記を使用）
- DuckDB、OpenAI SDK、defusedxml などを使用

推奨手順（プロジェクトルートから）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux) / .venv\Scripts\activate (Windows)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数
- 自動で .env / .env.local を読み込みます（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースはシェル風（export KEY=val、クォート、コメントの扱い）に対応します。

必須の環境変数（利用する機能に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（data.jquants_client が使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能など）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI を使う場合（ai.score_* 関数へは引数でも渡せます）

その他の設定（省略時はデフォルト）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

.env の自動読み込み順序
- OS 環境変数 > .env.local (override) > .env
- .env がプロジェクトルートに無ければ自動ロードはスキップされます

---

## 使い方（抜粋例）

まず DuckDB 接続を準備する例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行する:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースの NLP スコア付け（OpenAI API キーは env または api_key 引数で指定）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定している前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

市場レジーム判定:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログスキーマの初期化（監査用 DB を別ファイルで使う場合）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルを含む DuckDB 接続
```

研究モジュール例（モメンタム計算）:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は各銘柄ごとの dict のリスト
```

カレンダー関連ユーティリティ:

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print("営業日?", is_trading_day(conn, d))
print("翌営業日:", next_trading_day(conn, d))
```

品質チェックの実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

OpenAI 呼び出しのテスト時モック
- ai モジュール内では OpenAI 呼び出し箇所が内部関数を通しており、ユニットテストでは `_call_openai_api` を patch して差し替え可能です。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / .env 自動読み込み / settings
    - ai/
      - __init__.py
      - news_nlp.py  — ニュース NLP / score_news
      - regime_detector.py  — 市場レジーム判定 / score_regime
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（fetch/save）
      - pipeline.py  — ETL パイプライン（run_daily_etl など）
      - etl.py  — ETLResult 再エクスポート
      - calendar_management.py  — マーケットカレンダー管理
      - stats.py  — zscore_normalize など統計ユーティリティ
      - quality.py  — データ品質チェック
      - news_collector.py  — RSS 取得 / 前処理
      - audit.py  — 監査ログ DDL / init_audit_db
    - research/
      - __init__.py
      - factor_research.py  — ファクター計算
      - feature_exploration.py  — forward returns, IC, summary
    - research/*（補助関数）
- pyproject.toml (想定)
- .git (想定)
- .env / .env.local (任意。プロジェクトルートに置くと自動読み込み)

---

## 補足・運用ノート

- ルックアヘッド対策:
  - 多くの関数は内部で date.today() を参照せず、外部から target_date を受け取る設計です。バックテスト用途では必ず過去日時を与えてください。
- 冪等性:
  - J-Quants データ保存や監査テーブル初期化は冪等操作（ON CONFLICT / INSERT ... DO UPDATE 等）を採用しています。
- API レート／リトライ:
  - J-Quants は 120 req/min を想定して RateLimiter による制御を行います。OpenAI 呼び出しはリトライ・バックオフ処理があります。
- セキュリティ:
  - news_collector では SSRF 対策（ホストのプライベート判定、リダイレクト検査）や XML の安全パース（defusedxml）を行っています。
- テスト容易性:
  - OpenAI 呼び出し箇所やネットワーク入出力は内部関数を通しており、ユニットテスト時に簡単にモックできます。

---

もし README に含めたい追加のセットアップ手順（例: systemd サービス設定、監視ジョブ、Slack 通知例）、あるいは利用する外部パッケージの固定バージョン情報があれば教えてください。README をそれに合わせて追記します。