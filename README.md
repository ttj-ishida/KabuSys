# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLM を用いたニュース/レジーム評価・ファクター計算・データ品質チェック・監査ログなど、運用・研究・発注に必要な主要コンポーネントを含みます。

主な目的：
- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と LLM（OpenAI）による銘柄センチメント算出
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究用ファクター/特徴量計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェックと監査ログ（DuckDB ベース）

---

## 機能一覧

- 環境・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 必須環境変数チェック（Settings クラス）

- データプラットフォーム（data パッケージ）
  - J-Quants API クライアント（取得・保存・ページネーション・認証リフレッシュ・レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 防御・URL 正規化・重複排除）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（order_requests / executions / signal_events）

- 自然言語処理 / AI（ai パッケージ）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI により算出して ai_scores に保存
  - score_regime（regime_detector）: ETF(1321) の MA とマクロニュースの LLM センチメントを合成して market_regime に保存

- 研究支援（research パッケージ）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
  - 統計ユーティリティ: zscore_normalize

- 汎用ユーティリティ
  - data.stats.zscore_normalize
  - audit DB 初期化ユーティリティ（init_audit_db, init_audit_schema）

---

## セットアップ手順

以下は本リポジトリをローカルで動かすための基本手順です。プロジェクトに合わせて調整してください。

1. Python の準備
   - Python 3.10+ を推奨（typing union | を使用）

2. リポジトリのクローン／パッケージインストール
   - ソースツリーをクローン後、編集中であれば開発モードでインストール：
     - pip install -e .
   - または必要ライブラリを個別にインストール（例）:
     - pip install duckdb openai defusedxml

   （requirements.txt があればそれに従ってください）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で `.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   - 必須（運用で必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で利用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（該当機能使用時）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   - 推奨 / オプション:
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / regime_detector）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: データ DB パス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB の初期スキーマ
   - ETL・監査ログを使用するには DuckDB 接続を作り、必要に応じてスキーマ初期化を行ってください（例: audit テーブルの初期化は init_audit_db / init_audit_schema を使用）。

---

## 使い方（代表的な例）

以下はライブラリをプログラムから呼ぶ際の簡単な例です。

- DuckDB に接続して日次 ETL を回す（run_daily_etl）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査用 DuckDB の初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_kabusys.duckdb")
# conn は初期化済み DuckDB 接続
```

- 設定の参照:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- AI（OpenAI）呼び出しはネットワーク課金が発生します。api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl 等は外部 API と DB の両方にアクセスします。テスト時は ID トークンや外部クライアントをモックしてください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py              - パッケージ定義（version）
  - config.py                - 環境変数 / Settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py            - ニュースセンチメント算出（score_news）
    - regime_detector.py     - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（fetch / save）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー管理・バッチ
    - news_collector.py      - RSS ニュース収集
    - quality.py             - データ品質チェック
    - stats.py               - 統計ユーティリティ（zscore_normalize）
    - audit.py               - 監査ログスキーマ定義 / 初期化
    - etl.py                 - ETLResult の公開（簡易）
  - research/
    - __init__.py
    - factor_research.py     - モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py - 将来リターン / IC / 統計サマリー

（プロジェクトルートに pyproject.toml / setup.cfg / requirements.txt がある想定）

---

## テスト / モックについて

- OpenAI や外部 API 呼び出しはライブラリ内部の呼び出し点をモックしやすいよう分離されており、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen、jquants_client._request 等）を patch して利用できます。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストで有用）。

---

## 運用上の注意

- Look-ahead バイアス対策が各モジュールで注意深く実装されています（target_date 未満のみ参照、fetched_at を記録など）。バックテスト等で利用する場合はこの点を尊重して使用してください。
- DuckDB への executemany の空リスト制限や atomic な書き込みに関する実装上の前提があります（コード内コメント参照）。
- J-Quants API や OpenAI のレート制限・エラーに合わせたリトライロジックがありますが、運用でのスループットやコストには注意してください。

---

必要に応じて README に追加したい内容（例: CI の設定、具体的な DB スキーマ定義、サンプル .env.example、運用 runbook）を教えてください。