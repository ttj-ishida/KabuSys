# KabuSys

日本株向けのデータプラットフォーム兼自動売買ユーティリティ群です。  
J-Quants（株価・財務・カレンダー）、ニュース収集、LLM を利用したニュース NLP、リサーチ用ファクター群、ETL パイプライン、監査ログスキーマなどを含みます。

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダー等を差分で取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news / news_symbols）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位の ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究（research）向けのファクター計算・特徴量解析ユーティリティ
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- 取引監査（signal → order_request → execution）用の監査 DB スキーマ初期化ユーティリティ

設計上、バックテストにおけるルックアヘッドバイアスを避ける工夫（target_date を明示し datetime.today() を無暗に使わない等）や API の堅牢なリトライ / レート制御、冪等性重視の DB 保存が盛り込まれています。

## 主な機能一覧
- ETL
  - 日次 ETL（prices / financials / calendar）の差分取得と保存（kabusys.data.pipeline.run_daily_etl）
  - J-Quants クライアント（認証 / ページネーション / レート制限 / 保存関数）
- ニュース
  - RSS 収集（URL 正規化 / SSRF 対策 / gzip 対応）と raw_news への保存補助
  - ニュース前処理（URL 除去・空白正規化）
- AI（LLM）
  - 銘柄ごとのニュースセンチメントスコア生成（kabusys.ai.news_nlp.score_news）
  - マクロ + テクニカル（1321 MA200乖離）を使った市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（kabusys.research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）等の特徴量解析（kabusys.research.feature_exploration）
  - Z スコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質
  - 欠損・スパイク・重複・日付不整合検出（kabusys.data.quality）
- 監査ログ
  - 監査スキーマ初期化・専用 DB 作成（kabusys.data.audit.init_audit_schema / init_audit_db）

## 動作環境 / 依存関係
- 推奨 Python バージョン: 3.10+
  - （typing に `X | None` などの構文を使用）
- 主な依存パッケージ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib / json / logging 等を多用

例: requirements.txt の最小例
```
duckdb
openai
defusedxml
```

## セットアップ手順（ローカル開発向け）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install -U pip
   - pip install -r requirements.txt
   あるいはプロジェクト配布パッケージがある場合:
   - pip install -e .

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env、または .env.local を置くと自動ロードされます（モジュール起動時に自動で読み込み）。
   - 自動ロードを無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（例）:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

任意（デフォルトあり）:
- KABU_API_BASE_URL (default "http://localhost:18080/kabusapi")
- DUCKDB_PATH (default "data/kabusys.duckdb")
- SQLITE_PATH (default "data/monitoring.db")
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV ∈ {"development","paper_trading","live"} (default development)
- LOG_LEVEL ∈ {"DEBUG","INFO","WARNING","ERROR","CRITICAL"} (default INFO)

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

## 使い方（代表的な利用例）

- DuckDB 接続を作成して ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使った銘柄ニューススコアリング（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定しておく
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査用 DuckDB 作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を用いて監査ログを書き込み可能
```

- RSS フィードの取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# 収集した記事を raw_news テーブルへ保存する処理はアプリ側（ETL内の処理等）で行って下さい
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク負荷やコストが発生します。テスト時は該当関数をモックすることを推奨します（モジュール内で _call_openai_api 等を差し替える設計になっています）。
- ETL / 保存関数は DuckDB に対して冪等（ON CONFLICT DO UPDATE 等）で動作するよう設計されています。

## ディレクトリ構成（主要ファイル）
プロジェクトの主要なモジュールと役割を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py — ETF(1321) MA200 とマクロセンチメントを合成して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl）および個別 ETL ジョブ
    - etl.py — ETL 結果型の公開
    - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py — RSS 収集 / 前処理 / SSRF 対策
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン計算, IC, 統計サマリー
  - research/__init__.py — 研究向けユーティリティの再エクスポート

## 開発時の注意点 / ベストプラクティス
- API キーやパスワードは .env に保存し、リポジトリへコミットしないでください。
- テスト時は実ネットワーク呼び出しを避けるため、openai クライアントや urllib 呼び出しをモックしてください。モジュール内で _call_openai_api や _urlopen を差し替えられるよう設計されています。
- DuckDB の executemany に空のパラメータリストを渡すとバージョンによってエラーになる箇所があるため、本コードは空チェックを行っています。独自に拡張する際も注意してください。
- 監査スキーマ初期化は SET TimeZone='UTC' を実行します。DB のタイムスタンプは UTC を想定しています。

---

この README はコードベースの主要機能と代表的な使い方に焦点を当てています。実運用やデプロイ手順（systemd サービスや監視、Slack 通知等）は運用方針に合わせて別途記述してください。必要であれば具体的なデプロイ手順・例や .env.example を作成して追記できます。