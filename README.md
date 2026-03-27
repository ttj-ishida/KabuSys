# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ ETL、ニュース NLP（LLM を使ったセンチメント）、市場レジーム判定、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買や研究ワークフロー向けに設計された Python モジュール群です。  
主な目的は次のとおりです。

- J-Quants から株価・財務・マーケットカレンダー等を差分取得して DuckDB に保存する日次 ETL
- RSS を収集して raw_news に保存し、OpenAI（gpt-4o-mini）でニュースセンチメントを算出する NLP パイプライン
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ（IC, forward returns 等）
- 取引フローのための監査ログスキーマ（signal → order_request → executions）の初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴：
- DuckDB をメインの分析 DB として使用
- Look-ahead bias を避ける設計（内部で date.today() に無闇に依存しない）
- 外部 API 呼び出しにはリトライ／バックオフやレート制御を組み込み
- 冪等性を重視（INSERT ... ON CONFLICT 等）

---

## 機能一覧

- データ取得 / ETL
  - run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント：fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar（kabusys.data.jquants_client）
- ニュース収集 / NLP
  - RSS 収集と前処理（kabusys.data.news_collector）
  - ニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - score_regime（kabusys.ai.regime_detector）：ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成
- 研究用ユーティリティ
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン・IC・統計サマリー（kabusys.research）
  - z-score 正規化（kabusys.data.stats.zscore_normalize）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（kabusys.data.quality）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）で監査テーブルを初期化

---

## セットアップ手順

前提
- Python 3.10 以上（`|` 型ヒントを使用しているため）
- DuckDB、OpenAI SDK などが必要

1. レポジトリをクローン（またはソースを入手）してプロジェクトルートに移動：
   - 例: git clone ... && cd kabusys

2. 仮想環境を作成・有効化（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール（最低限）:
   - pip install duckdb openai defusedxml

   ※ 実行環境に応じて追加パッケージが必要になる可能性があります（例: テスト用モック等）。

4. 開発インストール（ソースから使う場合）:
   - プロジェクトルートに setup.cfg/pyproject があれば:
     - pip install -e .
   - ない場合は、上の依存パッケージをインストールした上で PYTHONPATH に src を追加するか、パッケージを適宜インストールしてください。

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、kabusys.config が自動でロードします（プロジェクトルートは .git または pyproject.toml を探索して判定）。
   - 自動ロードを無効化したい場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルト有り）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

サンプル .env（プロジェクトルート）:
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=jq-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要な例）

以下は簡単な利用例です。import する前に必要な環境変数が設定されていることを確認してください。

1) DuckDB 接続の取得（settings.duckdb_path を利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントスコアの算出（ai -> ai_scores テーブルへ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続
count = score_news(conn, target_date=date(2026,3,20))
print(f"wrote scores for {count} codes")
```

4) 市場レジームのスコア算出（market_regime テーブルへ書き込み）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

5) 監査ログ用 DB の初期化（別ファイルを使う / :memory: も可）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成される
```

6) 研究用ファクター計算例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

注意点：
- AI モジュールは OpenAI の API を呼び出します。API キーは `OPENAI_API_KEY` または各関数の `api_key` 引数で渡してください。
- J-Quants API は rate limit やトークンリフレッシュを内部で扱いますが、`JQUANTS_REFRESH_TOKEN` が必要です。
- ETL / NLP は外部 API の失敗に対してフェイルセーフを取る（スキップして継続）実装になっている箇所が多いです。ログを確認してください。

---

## 主要モジュール（クイックリファレンス）

- kabusys.config
  - settings: 各種設定プロパティ（jquants_refresh_token / duckdb_path / env / log_level 等）
  - .env 自動読み込み（OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）
- kabusys.data
  - jquants_client: J-Quants API クライアント + DuckDB 保存関数
  - pipeline: run_daily_etl 等の ETL パイプライン
  - news_collector: RSS 取得・前処理
  - calendar_management: 市場カレンダー関数（is_trading_day / next_trading_day 等）
  - quality: データ品質チェック
  - audit: 監査テーブル初期化ユーティリティ
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: ニュース NLP バッチ処理
  - regime_detector.score_regime: 市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュース NLP（score_news）
    - regime_detector.py                -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py                 -- RSS 収集と前処理
    - calendar_management.py            -- 市場カレンダー関連ユーティリティ
    - quality.py                        -- データ品質チェック
    - audit.py                          -- 監査ログスキーマ初期化
    - etl.py                            -- ETLResult のエクスポート
    - stats.py                          -- 汎用統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py                -- ファクター計算
    - feature_exploration.py            -- 将来リターン / IC / 統計サマリー

（上記はコードベースの主要モジュールを示しています）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は `.env` に平文で置く運用に注意（機密情報の管理は適切に）。
- 本番環境では `KABUSYS_ENV=live` を設定し、テスト・ペーパートレード用の分離を行ってください。
- OpenAI 呼び出しはコストとレート制限に注意。バッチサイズやリトライパラメータはコード内定数で調整可能です。
- DuckDB のファイルは定期的にバックアップしてください。監査データは削除しない前提の設計です。
- ETL の実行ログと品質チェック結果は必ず監視し、品質問題が検出された場合は原因を突き止めてから次フェーズへ進めてください。

---

## さらに

- テストや CI で自動 .env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 各モジュールはモジュール内で単体テストが行いやすい設計（関数引数で API キー注入や Sleep の差し替えが可能）になっています。ユニットテストを書く際は該当箇所をモックしてください。

---

必要であれば、README に追加したい内容（例: 詳細な API リファレンス、テーブルスキーマ一覧、実行スケジュール例、サンプル .env.example のテンプレートなど）を教えてください。