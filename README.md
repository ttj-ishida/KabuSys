# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（パッケージ）。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、監査ログ構築などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を含む Python パッケージです。

- J-Quants API からの差分データ取得（株価日足 / 財務 / マーケットカレンダー）
- DuckDB を用いたデータ保存と ETL パイプライン（冪等保存、品質チェック付き）
- ニュース収集（RSS）および LLM を用いたニュース・センチメント評価（gpt-4o-mini を想定）
- ETF とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化
- 環境設定の一元管理（.env 自動読み込み機能）

設計上の特徴：
- ルックアヘッドバイアスを避けるため、date を明示して処理する設計（date.today() を直接参照しない箇所が多い）
- DuckDB SQL を多用し、高速に集計・ウィンドウ処理を行う
- 冪等性を優先した DB 書き込み（ON CONFLICT / DELETE→INSERT）設計
- 外部 API 呼び出しに対するリトライやバックオフ、フェイルセーフを組み込んでいる

---

## 機能一覧

主なモジュールと提供機能の概要：

- kabusys.config
  - .env / .env.local の自動ロード（プロジェクトルート判定）
  - settings オブジェクト経由で環境変数アクセス（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY 想定）
  - 自動ロードの無効化は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・ページング・リトライ・トークン自動リフレッシュ）
  - fetch / save 関数（daily_quotes, financial_statements, market_calendar, listed_info）
  - DuckDB への冪等保存関数

- kabusys.data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の日次 ETL パイプライン
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult クラスで結果を集約

- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合のチェック関数と総合実行 run_all_checks

- kabusys.data.news_collector
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF対策、gzip上限、トラッキング除去等）

- kabusys.ai.news_nlp
  - score_news: raw_news を銘柄別に集約し LLM でセンチメント評価して ai_scores に書き込む
  - OpenAI JSON Mode（gpt-4o-mini）を想定、バッチ処理・リトライ付き

- kabusys.ai.regime_detector
  - score_regime: ETF（1321）の 200 日移動平均乖離とマクロニュースのセンチメントを合成し市場レジームを判定、market_regime に保存

- kabusys.research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン・IC・統計サマリ（calc_forward_returns / calc_ic / factor_summary / rank）
  - zscore_normalize（data.stats からも利用可能）

- kabusys.data.audit
  - 監査ログ向けテーブル DDL / インデックスの初期化（init_audit_schema / init_audit_db）
  - signal → order_request → executions のトレーサビリティ設計

---

## 必須依存ライブラリ（主なもの）

実行には以下のパッケージが必要です（抜粋）:

- Python 3.10+（typing の | を使用）
- duckdb
- openai（OpenAI の新しい SDK を想定）
- defusedxml

その他、標準ライブラリのみで HTTP・XML を扱う実装になっています。実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージを入手

2. 仮想環境を作成して依存をインストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成することで自動ロードされます。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数でも渡せます）
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
   - 自動 .env ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（監査ログ等）
   - 監査専用 DB を作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 既存 DuckDB 接続に監査スキーマを適用する:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（代表的なコード例）

以下は最小限の利用イメージです。適宜例外処理やログ設定を追加してください。

- 基本準備（DuckDB 接続と settings）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（AI）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数で設定するか、api_key 引数に渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores for {n_written} codes")
```

- 市場レジーム判定

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究用ユーティリティ

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

mom = calc_momentum(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 監査 DB 初期化（例）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD (必須 if using kabu API) — kabu API パスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 if Slack integration)
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログ出力レベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

注意: .env の自動読み込みは package 内の config モジュールがプロジェクトルート（.git または pyproject.toml を探索）を検出した場合に行います。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル / モジュール構成（提供コードに基づく）:

- src/kabusys/
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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - (その他: pipeline で使用する quality, schema など)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor/feature 関数）
- pyproject.toml / setup.cfg / requirements.txt （プロジェクトに合わせて）

この README の内容はコード上の docstring とコメントに基づいてまとめています。実行時には各モジュールの docstring・関数シグネチャを参照してください。

---

## 運用上の注意・ベストプラクティス

- OpenAI 呼び出しは API レートやコストに注意して運用してください。score_news はバッチ処理（最大 BATCH_SIZE）で呼ぶ設計です。
- DuckDB ファイルは適切にバックアップしてください（特に監査ログは削除前提でない設計）。
- ETL は外部 API の一時的な失敗に対して堅牢に設計されていますが、重大な品質問題（QualityIssue.severity="error"）が検出された場合は手動確認を推奨します。
- 本ライブラリの関数はルックアヘッドを避ける設計ですが、呼び出し側で target_date を誤って未来日付にすることがないよう運用ルールを設けてください。

---

もし README に追加したい具体的なサンプル（Docker / CI／CD / 実運用の設定例）や、requirements.txt / pyproject.toml の内容があれば、追記してより詳細なセットアップ手順を作成します。