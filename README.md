# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API（市場データ）、DuckDB ベースのローカルデータ管理、ニュースの NLP スコアリング（OpenAI）、リサーチ用のファクター計算、監査ログ（オーダー/約定トレーサビリティ）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するためのモジュール群をまとめたライブラリです。主に以下を目的としています。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB によるローカル ETL / データ品質チェック
- RSS を使ったニュース収集と OpenAI を用いたニュースセンチメント評価
- マクロセンチメントとテクニカル指標を組み合わせた市場レジーム判定
- ファクター生成・リサーチ用ユーティリティ（モメンタム、バリュー、ボラティリティ等）
- 発注〜約定まで追跡可能な監査ログスキーマの初期化・管理

設計上の特徴として、ルックアヘッドバイアス回避、冪等性（ETL/保存処理）、API リトライ・レート制御、フェイルセーフ（API 失敗時のフォールバック）を備えています。

---

## 主な機能一覧

- 環境設定管理（自動 .env ロード、必須 env チェック）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_* 系で DuckDB へ冪等保存
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETL 結果は ETLResult で集約
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（URL 除去、正規化、SSRF 対策）
- ニュース NLP（OpenAI）
  - score_news: 銘柄単位のニュースセンチメントスコアを ai_scores に書き込み
  - JSON モード、バッチ化、リトライ、レスポンスバリデーション
- 市場レジーム判定
  - score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- リサーチ用ユーティリティ
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db: signal_events / order_requests / executions を作成し監査トレーサビリティを提供
- マーケットカレンダー用ユーティリティ（is_trading_day 等）

---

## セットアップ手順

前提: Python 3.10+（型アノテーションで union 型や typing の機能を使用）

1. リポジトリをクローン / ソースを配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - 必要な主要パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   実プロジェクトでは requirements.txt / pyproject.toml を用意してインストールしてください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須と任意を区別）:

     必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（システムで Slack を使う場合）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知先）
     - KABU_API_PASSWORD     : kabu API パスワード（kabu ステーション連携がある場合）

     任意 / デフォルトあり:
     - KABUSYS_ENV           : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動読み込みを無効化
     - KABUSYS... 他（必要に応じて）

     DB パス:
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視等）パス（デフォルト data/monitoring.db）

   - .env のフォーマットは通常の KEY=VALUE 形式（export プレフィックスやクォートもサポート）。

---

## 使い方（簡易サンプル）

以下は Python インタープリタやスクリプトから簡単に使う例です。DuckDB 接続を作成して各機能を呼び出します。

1) ETL を日次で実行する（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースのセンチメントスコアを計算して ai_scores に保存（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定を実行（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続を返す
```

5) J-Quants から株価を取得して保存（低レベル呼び出し）

```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect('data/kabusys.duckdb')
records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = jq.save_daily_quotes(conn, records)
```

注意: OpenAI の呼び出しや J-Quants API 呼び出しは API キーが必要です。ライブラリでは再試行やバックオフを実装していますが、API 利用料・レート制限に注意してください。

---

## 設定・環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 関連関数) - OpenAI API キー（score_news / score_regime 等）
- KABU_API_PASSWORD (必須 if using kabu API)
- KABU_API_BASE_URL (任意) - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID - Slack 通知設定
- DUCKDB_PATH (任意) - DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) - SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV - execution 環境（development / paper_trading / live）
- LOG_LEVEL - ログレベル

.env ファイルはプロジェクトルート（.git や pyproject.toml のあるディレクトリ）で自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 配下の主要モジュールと役割の概略です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): ニュースセンチメントを ai_scores に書き込み
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): 市場レジーム判定を market_regime に書き込み
  - data/
    - __init__.py
    - calendar_management.py
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
    - etl.py
      - ETLResult 再エクスポート
    - pipeline.py
      - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
    - stats.py
      - zscore_normalize
    - quality.py
      - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
    - audit.py
      - init_audit_schema / init_audit_db（監査ログテーブル定義）
    - jquants_client.py
      - J-Quants API クライアント（fetch_*/save_* や get_id_token）
    - news_collector.py
      - fetch_rss / RSS パース・前処理・SSRF 対策
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

---

## 設計上の注意点・ベストプラクティス

- ルックアヘッドバイアス回避: 多くの関数は date.today() 等を内部で参照せず、外部から target_date を渡す設計です。バックテスト時は必ず過去日時を渡して評価してください。
- 冪等性: save_* 関数は ON CONFLICT を活用して同一キーの再保存を安全に処理します。
- API キー管理: OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN は環境変数で管理し、外部に漏れないようにしてください。
- テスト容易性: OpenAI の実際の呼び出しは内部関数を差し替えやすく設計（unittest.mock.patch）されています。
- エラーハンドリング: 外部 API はリトライを行いますが、最終的に取得できなかった場合はフェイルセーフ（ゼロ値やスキップ）となる箇所があります。ログを確認し必要に応じて手動対応してください。

---

## 追加情報 / 今後の拡張

- Strategy（発注戦略）や Execution（ブローカー連携）は別モジュールとして統合予定（README の __all__ に "strategy", "execution", "monitoring" が含まれています）。
- 監査ログを用いた実際の発注フロー、Slack 通知、kabu ステーションとの連携サンプルは今後追加予定です。

---

問題や不明点があれば、使いたいユースケース（例：バックテスト、リアル運用、ニューススコアのみ等）を教えてください。必要に応じて具体的な設定例や運用手順を追記します。