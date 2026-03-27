# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
DuckDB を内部データストアとして用い、J-Quants API からのデータ取得、ニュースの収集と LLM による NLP スコアリング、ファクター計算、ETL パイプライン、監査ログ（注文→約定のトレーサビリティ）などを提供します。

## 概要

KabuSys は以下のような機能群を含むモジュール群で構成されています。

- データ取得・ETL（J-Quants 連携、ニュース収集、カレンダー管理）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算・リサーチユーティリティ（モメンタム・バリュー・ボラティリティ等）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 環境設定管理（.env / 環境変数読み込み）

## 主な機能一覧

- ETL:
  - run_daily_etl（市場カレンダー、株価日足、財務データの差分取得・保存・品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質:
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- ニュース:
  - RSS 収集（fetch_rss）、raw_news 保存、news_symbols との紐付け
  - score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores へ書込）
- 市場レジーム:
  - score_regime: ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM 評価を合成して daily の market_regime を書き込み
- 研究 / ファクター:
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査ログ:
  - init_audit_schema / init_audit_db による監査テーブル作成（冪等、UTC タイムスタンプ）
- J-Quants クライアント:
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

## 前提 / 必要な環境

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI 等）

（プロジェクトの requirements.txt がある場合はそれを利用してください。ここでは主要依存のみ例示しています。）

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt があればそれを使用）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN        : Slack 通知に使用（必要に応じて）
     - SLACK_CHANNEL_ID       : Slack チャネル ID
     - KABU_API_PASSWORD      : kabuステーション API パスワード
     - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 等で使用）
   - 任意 / 既定値:
     - KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL      : kabusation API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            : SQLite（監視用 DB など）のパス（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 基本的な使い方（コード例）

- DuckDB 接続の作成（settings.duckdb_path を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます（内部で営業日に補正あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニューススコアリング（OpenAI API KEY が必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored {n_written} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査監視用 DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可
```

- ファクター計算（research）
```python
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注:
- score_news / score_regime 等の AI 呼び出しは OpenAI API を使用します。API 呼び出しに失敗した場合はフェイルセーフでスコアを 0 にフォールバックする実装が含まれます。
- ETL / 保存処理は基本的に冪等（ON CONFLICT DO UPDATE 等）で、安全に再実行できます。

## 主要モジュール（ディレクトリ構成）

リポジトリ内の主要ファイル・ディレクトリは以下のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / .env 自動読み込み・設定アクセス
  - ai/
    - __init__.py
    - news_nlp.py            : ニュースの LLM スコアリング（score_news）
    - regime_detector.py     : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（fetch_*/save_*）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - etl.py                 : ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py : 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py      : RSS ニュース収集
    - quality.py             : データ品質チェック
    - stats.py               : zscore_normalize 等の統計ユーティリティ
    - audit.py               : 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     : モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - ai/, data/, research/ 以下に logger 設計、DB 操作（DuckDB）中心の処理が実装されています。

ルートの構成例:
- pyproject.toml / setup.py（パッケージ設定）
- .env.example（存在する場合）
- src/kabusys/（ライブラリ実装）

## 注意事項 / 実運用上のポイント

- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかを想定しています。live 実行時は特に注意してください（発注・金銭取引を伴う場合）。
- OpenAI / J-Quants / kabustation など外部 API のレート制限や課金に注意。J-Quants クライアント・news_nlp/regime_detector にはリトライ・レート制御が組み込まれていますが、利用ポリシーは厳守してください。
- ニュース収集では SSRF 対策や XML の安全パース（defusedxml）を行っていますが、フィードソースの信頼性を考慮してください。
- DuckDB による ETL / 保存は基本的に冪等であることを前提に設計されていますが、バックアップや運用監視は適切に行ってください。
- 自動的に .env を読み込む仕組みはプロジェクトルートを基準に検出します。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。

---

この README はコードの主要な機能・使い方を簡潔にまとめたものです。さらに詳細な利用法や API の仕様（J-Quants のレスポンス形式、テーブルスキーマ等）は各モジュールの docstring を参照してください。必要なら README に追記する点（例: 実行例スクリプト、CI 設定、requirements.txt）を教えてください。