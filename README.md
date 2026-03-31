# KabuSys

日本株のデータプラットフォームと自動売買・リサーチ基盤を想定した Python パッケージ群です。  
データ ETL、ニュース NLP（LLM を使ったセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル、ページネーション対応、API レート制御、トークン自動リフレッシュ
- ニュース収集・NLP
  - RSS からニュース取得（SSRF対策・サイズ制限・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores への書込み）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン算出、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合（未来日付／非営業日のデータ）を検出
- 監査ログ（Audit / トレーサビリティ）
  - signal → order_request → execution に至る監査テーブルの初期化と管理（DuckDB）
- 設定管理
  - .env / 環境変数から設定を自動ロード（プロジェクトルート検出、.env.local優先など）
  - 必須設定の明示・検証

---

## 必要要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ：urllib, json, logging, datetime など）

ローカルで動かす最低限のインストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

※ パッケージが setup 配下で管理されている場合は `pip install -e .` で開発インストール可能です。

---

## セットアップ手順

1. リポジトリをクローン／取得してプロジェクトルートに移動する。
2. 仮想環境を作成して有効化する（推奨）。
3. 依存ライブラリをインストールする（上記参照）。
4. 環境変数を設定する（.env をプロジェクトルートに置くことで自動読み込みされます）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. DuckDB 等のデータベースディレクトリを用意する（デフォルトは data/ 以下）。

### 推奨する .env の例
プロジェクトルートに `.env` または `.env.local` を配置して下さい（`.env.local` は `.env` を上書きする目的で使用可能）。

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu API（kabuステーション連携がある場合）
KABU_API_PASSWORD=your_kabu_api_password
#KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# OpenAI
OPENAI_API_KEY=sk-...

# DB パス（任意: デフォルトは data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb

# 環境
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
```

必須の環境変数（Settings で検証される）
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD

OpenAI API を使う機能を利用する場合は `OPENAI_API_KEY` を設定してください。

---

## 使い方（簡単な利用例）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続は設定のパスを使うのが便利です。

- 日次 ETL の実行（株価・財務・カレンダー取得＋品質チェック）
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）スコアリング
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示するか環境変数 OPENAI_API_KEY を設定する
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（ETF 1321 を参照）
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（監査専用 DB を分けたい場合）
```
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 別ファイルに監査DBを作る例（:memory: も可）
audit_conn = init_audit_db("data/audit.duckdb")
```

- 研究（ファクター計算・IC 等）
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
momentum = calc_momentum(conn, target)
forward = calc_forward_returns(conn, target)
ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
```

---

## 設定と環境（Settings）

`kabusys.config.settings` を通して各種設定値にアクセスできます。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password / kabu_api_base_url: kabu ステーション API 設定
- slack_bot_token / slack_channel_id: Slack 通知
- duckdb_path / sqlite_path: DB ファイルパス（Path オブジェクト）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- is_live / is_paper / is_dev: 環境判定ヘルパ

自動で .env/.env.local をプロジェクトルート（.git または pyproject.toml のある親）から読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

リポジトリ内の主要なパッケージ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py (パッケージエクスポート)
  - config.py
    - 環境変数読み込み・Settings 定義 (.env 自動ロード)
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを集約して OpenAI で銘柄別センチメントを算出し ai_scores に保存
    - regime_detector.py
      - ETF（1321）の MA 乖離とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、レート制御、リトライ）
    - pipeline.py
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
      - ETLResult データクラス
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF・サイズ対策）
    - calendar_management.py
      - market_calendar の管理、営業日判定 (is_trading_day, next_trading_day, ...)
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

各モジュールは設計文書（コメント）に沿って「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」「DuckDB を想定した SQL 処理」を重視して実装されています。

---

## 注意事項 / 運用上のポイント

- OpenAI を利用する処理は API 呼び出し回数やコストが発生します。batch サイズや頻度を設定で調整してください。
- J-Quants API のレート制限を順守するため内部に RateLimiter を実装していますが、運用時は API キーや制限に注意してください。
- 本コード群はデータ取得・解析基盤を提供するもので、実際の発注（ブローカーへの本番注文）を行う層は別途実装が必要です。KABU API 関連の設定は用意されていますが、実際の注文ロジック・安全機構は利用者側で実装・確認してください。
- DuckDB のバージョン差異（executemany の挙動等）に注意が必要な箇所があります（コード内に注意書きあり）。

---

README は以上です。必要であれば、セットアップ手順の詳細化（requirements.txt、CI 設定、例の .env.example ファイルの追加）、具体的な運用フロー（スケジューラ / cron / Airflow 例）やテスト実行方法を追記します。どの情報を優先して追加しますか？