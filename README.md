# KabuSys

日本株向けの自動売買＆データプラットフォームライブラリ。ETL、ニュースNLP（LLM を用いたセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレース）などを提供します。

## 主な特徴
- ETL（J-Quants API）による株価・財務・マーケットカレンダーの差分取得と DuckDB 保存（冪等）
- ニュースセンチメント（OpenAI / gpt-4o-mini）による銘柄別 ai_score 生成（batch 処理・リトライ付き）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量評価ツール（IC, forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）用ユーティリティ（SSRF 対策・トラッキング除去・サイズ制限）
- 監査ログスキーマ（signal → order_request → execution の完全トレース）と初期化ユーティリティ
- 環境設定管理（.env 自動読み込み、環境変数経由）

---

## 必要条件
- Python 3.10+
- DuckDB
- OpenAI Python SDK
- defusedxml
（実行環境に応じて他のライブラリが必要になる場合があります。パッケージ化された requirements.txt を参照してください）

概ね利用する主要ライブラリ：
- duckdb
- openai
- defusedxml

---

## インストール（開発環境向けの例）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（プロジェクトに requirements.txt がある想定）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または
pip install duckdb openai defusedxml
```

パッケージとしてローカルにインストールする場合:
```bash
pip install -e .
```

---

## 環境変数 / 設定
kabusys は .env ファイルまたは環境変数から設定を読み込みます（src/kabusys/config.py）。

自動ロードの優先順位:
- OS 環境変数
- .env.local（存在すれば上書き）
- .env

自動ロードを無効化するには:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime に必要）
- KABU_API_PASSWORD     : kabuステーション API 用パスワード
- KABU_API_BASE_URL     : kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live）
- LOG_LEVEL             : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

注意: .env のパースは export KEY=val 形式、引用符やコメント（#）処理を考慮した実装になっています。

---

## セットアップ（DB 初期化等）
監査ログ用の DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
# conn は duckdb.DuckDBPyConnection
```

データプラットフォーム向けのメイン DuckDB に対するスキーマ初期化やテーブル作成はプロジェクト別のスキーマ初期化関数（本リポジトリに含まれる場合）を利用してください。

---

## 使い方（主要 API 例）

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 ai_scores 生成）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジームスコア計算
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーを環境変数で渡す
```

- ニュース RSS 取得（前処理済み記事リストを返す）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査 DB の初期化（監査テーブル群を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- 研究（Research）モジュール例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 主要モジュールと機能一覧
（抜粋）
- kabusys.config
  - 環境変数・.env 読み込み、Settings クラス
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（token refresh・pagination・rate limit・保存関数）
  - fetch_*, save_* 系関数
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（結果型）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.news_collector
  - fetch_rss、URL 正規化、SSRF 対策、前処理
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - 監査ログテーブル DDL、init_audit_schema / init_audit_db
- kabusys.ai.news_nlp
  - score_news（LLM を用いた銘柄別センチメント）
- kabusys.ai.regime_detector
  - score_regime（MA200 とマクロ LLM を合成）
- kabusys.research
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.stats
  - zscore_normalize 等の統計ユーティリティ

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (公開 ETL インターフェース)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research 等（factor/feature utilities）

（README 用に主要モジュールのみ抜粋しています。実際のリポジトリはさらにモジュールや補助ファイルが含まれる可能性があります。）

---

## 運用上の注意・ベストプラクティス
- API キー（OpenAI / J-Quants）は必ず環境変数や安全なシークレット管理で運用してください。ログやコードに直接埋め込まないでください。
- LLM 呼び出しはコストとレート制限の影響を受けるため、バッチ化・リトライ設定を調整してください。
- DuckDB ファイルは定期バックアップを推奨します。監査ログは削除しない運用を前提としています。
- ETL・LLM 呼び出しは再現性確保のため、バックテスト時に Look-ahead Bias を避ける設計になっています（関数は date パラメータで明示的に対象日を受け取ります）。
- news_collector の fetch_rss は外部 URL を扱うため SSRF 対策・サイズ・XML の脆弱性対策が組み込まれています。外部フィード追加時は source と URL の妥当性を確認してください。

---

## さらに詳しく
各モジュールの docstring と関数コメントが詳細な設計方針・エッジケース処理を記述しています。実運用や拡張の際は該当ファイル（例: data/jquants_client.py、ai/news_nlp.py、data/pipeline.py）を参照してください。

ご要望があれば、セットアップ用の requirements.txt やサンプル .env.example、簡易のデータベーススキーマ初期化スクリプト等も作成します。必要なものを教えてください。