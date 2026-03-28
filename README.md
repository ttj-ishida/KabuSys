# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ管理、マーケットカレンダー管理、AI（OpenAI）を用いたニュースセンチメント評価や市場レジーム判定などを含みます。

---

## 主要機能

- ETL
  - J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次パイプラインの実行（run_daily_etl）
- データ管理
  - market_calendar（営業日判定）、raw_prices/raw_financials/raw_news 等の取り扱いヘルパー
  - DuckDB への保存ユーティリティ（save_*）
  - 監査ログ（signal_events, order_requests, executions）テーブルの初期化・管理
- ニュース収集
  - RSS フィード収集（SSRF対策、トラッキング除去、前処理）
- AI（OpenAI）
  - ニュースごとの銘柄センチメント評価（score_news）
  - マクロ + ETF（1321）MA200乖離を組み合わせた市場レジーム判定（score_regime）
  - バッチ・リトライ・レスポンスバリデーション対応
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- ユーティリティ
  - 環境変数・設定読み込み（.env 自動読み込み機能）
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - ニュース収集のセキュリティ対策（SSRF・XML攻撃等）

---

## 必要条件 / 依存ライブラリ（抜粋）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外は pyproject.toml / requirements に合わせてインストールしてください）

例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等で必要）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視データベース（監視用途）

README に合わせて `.env.example` を作成しておくことを推奨します。

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動
2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows
   ```
3. 依存関係をインストール
   ```
   pip install -e .            # パッケージとして開発インストール（pyproject.toml がある場合）
   # または必要パッケージを個別にインストール
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参考に）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     ```
5. 必要なディレクトリを作成（DuckDB 等の格納先）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから呼び出す例です。各関数は duckdb 接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB 接続の作成（設定からパスを使用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）で銘柄ごとのスコアを生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数または api_key 引数で渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", num_written)
```

- 市場レジーム判定（ma200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化（個別に監査用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

- RSS を取得して raw_news に保存するワークフロー（概念）
  - RSS 取得: fetch_rss (kabusys.data.news_collector.fetch_rss)
  - 前処理・ID 生成・DB 保存処理はモジュール内ロジックに従う

---

## 注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止のため、全モジュールは内部で datetime.today() を直接使わないよう設計されています。必ず target_date を外部から渡して実行してください。
- OpenAI 呼び出しは JSON モードを使い、結果のバリデーション（パース・スコアのクリップ等）を行います。API エラー時はフェイルセーフ（0.0 等）で継続する設計です。
- J-Quants クライアントはレートリミット（120 req/min）を守るための簡易レートリミッタと、401 の場合のトークン自動リフレッシュ、429 等の指数バックオフを実装しています。
- ニュース収集では SSRF / XML bomb / 大きすぎるレスポンスなどのセキュリティ対策を組み込んでいます。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）にしています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py             — ニュースセンチメント生成（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch/save 関数）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETL ユーティリティ再エクスポート
  - news_collector.py       — RSS 収集・前処理
  - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
  - quality.py              — 品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py      — Momentum / Value / Volatility 計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- ai, monitoring, strategy, execution 等（パッケージ公開対象として __all__ に定義）

---

## 開発 / テストヒント

- 環境変数の自動ロードは config.py によって行われます。テスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部で _call_openai_api を使っています。ユニットテストでは該当関数をモックして API 呼び出しをシミュレートできます（例: unittest.mock.patch）。
- DuckDB に対してはインメモリ接続 `duckdb.connect(":memory:")` を使うとテストが容易です。
- ニュース収集の外部 HTTP はモックまたはローカルファイルでテストすることを推奨します（SSRFチェック等を含むため）。

---

## 参考 / 今後の作業

- 発注（kabuステーション）連携、ポジション管理、リスク管理、運用監視ダッシュボードとの統合は別モジュール（execution, monitoring）で展開予定です。
- .env.example や SQL スキーマのドキュメント、運用手順（Cron / Airflow ジョブ定義）を整備してください。

---

この README はコードベースの主要な用途と操作方法をまとめたものです。実行する前に必須環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定し、DuckDB パス等を確認してください。必要なら README をプロジェクト運用ルールに合わせて追補してください。