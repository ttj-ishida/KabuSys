# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレース）などのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームおよびリサーチ／自動売買基盤を構成するためのモジュール群です。主な役割は以下です。

- J-Quants API からの株価・財務・カレンダーデータの差分取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別）とマクロセンチメント合成による市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）計算・特徴量解析および正規化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- 環境変数管理と .env 自動ロード（プロジェクトルートに依存）

設計上の特徴として、ルックアヘッドバイアス回避や冪等性、ネットワーク・API の堅牢なリトライ・レート制御が盛り込まれています。

---

## 主な機能一覧

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を表す ETLResult データクラス
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュ対応）、内部的にレートリミッタ・リトライ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策）、記事正規化、記事ID生成
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付整合性チェック、QualityIssue オブジェクト
- 監査ログ（kabusys.data.audit）
  - 監査用テーブル定義、初期化関数（init_audit_schema / init_audit_db）
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize
- AI モジュール（kabusys.ai）
  - score_news（銘柄別ニュースセンチメントを ai_scores テーブルへ保存）
  - score_regime（ETF 1321 の MA とマクロセンチメントを合成して market_regime を更新）
- リサーチ補助（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理（kabusys.config）
  - .env/.env.local 自動ロード（プロジェクトルートベース）、Settings オブジェクト（環境変数アクセス）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントに | 演算子等を使用）
- システムに pip がインストール済みであること

1. リポジトリをクローン／配置

   git リポジトリからのインストールや開発時はプロジェクトルート（.git または pyproject.toml が存在する場所）を用意してください。

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール（例）

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます（kabusys.config が .git または pyproject.toml を基にプロジェクトルートを探索してロード）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知に使う場合
- SLACK_CHANNEL_ID — Slack 通知に使う場合
- KABU_API_PASSWORD — kabuステーション連携用パスワード（利用時）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- OPENAI_API_KEY — OpenAI を使う関数のデフォルト（score_news / score_regime）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python REPL もしくはスクリプト内で使う例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の作成例

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 指定日（None なら today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- 個別 ETL ジョブ（株価のみ）

```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
print(fetched, saved)
```

- ニュースのスコアリング（OpenAI API キーが必要）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# score_news は raw_news / news_symbols / ai_scores テーブルを参照・更新します
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使用
print("scored:", count)
```

- 市場レジームの判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログスキーマの初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

- リサーチ関数の利用例（ファクター計算 → 正規化 → IC）

```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

date0 = date(2026, 3, 20)
momentum = calc_momentum(conn, date0)
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
ic = calc_ic(normalized, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点:
- AI を使う処理（score_news / score_regime）は OpenAI API のレスポンス依存のため、API キーや呼び出し成功時のレスポンス形式に注意してください。失敗時はフェイルセーフでスコア 0.0 を扱う等の設計になっています。
- ETL は差分取得とバックフィルを行います。run_daily_etl はカレンダーを取得してから株価・財務を取得し、最後に品質チェックを行います。

---

## よく使う公開 API（抜粋）

- kabusys.config.settings — 環境変数ラッパー
- kabusys.data.pipeline.ETLResult, run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
- kabusys.data.news_collector.fetch_rss
- kabusys.data.quality.run_all_checks
- kabusys.data.audit.init_audit_schema / init_audit_db
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.* のファクター・解析関数群

---

## ディレクトリ構成

プロジェクトの主要ファイル／モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他: etl を補助するモジュール群)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - (その他トップレベルモジュール: strategy, execution, monitoring が __all__ に示唆されていますが、本リストには data/research/ai 等を中心に含んでいます)

（上記はコードベースから抽出した主要ファイル群です。開発中のサブモジュールや将来的な拡張が存在する可能性があります。）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は `.env` / `.env.local` に保存し、機密情報は適切に管理してください（Git 管理除外など）。
- OpenAI / J-Quants の API キーは権限管理に注意してください。API コストやレート制限に注意して利用してください。
- ETL や AI 呼び出しは外部 API に依存するため、ジョブは再試行・監視・ロギングを行うことを推奨します。
- DuckDB のスキーマ初期化や監査ログ作成は運用開始時に実行してください（kabusys.data.audit.init_audit_db / init_audit_schema）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動 .env ロードをオフにすると意図しない設定漏れを防げます。

---

必要であれば、README に追加で以下の内容を追記できます:
- 開発環境構築（pyproject.toml / pre-commit / linters）
- 具体的な DB スキーマ定義（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）
- 運用用 systemd / cron でのジョブ例
- テストの実行方法とモックの置き方（OpenAI / J-Quants 呼び出しのモック方法）

ご希望があれば、上のいずれかを追記して詳細な手順例・サンプルスクリプトを作成します。