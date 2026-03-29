# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション / OpenAI を組み合わせて、データ取得（ETL）・品質検査・ニュースNLP・市場レジーム判定・監査ログ管理などを行うためのモジュール群を提供します。

この README はリポジトリ内の src/kabusys 以下のコードベースに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株向けのアルゴリズムトレーディングのための基盤ライブラリです。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- raw_news を収集・前処理し OpenAI によるニュース sentiment / 銘柄別 AI スコアを生成するニュースNLP
- ETF（1321）の MA 乖離とマクロニュースの LLM センチメントを合成した市場レジーム判定
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレース可能なテーブル）初期化ユーティリティ
- 研究用途（ファクター計算、将来リターン、IC 計算、Z スコア正規化等）

安全性と再現性に配慮し、外部 API の呼び出しにはリトライ、レート制御、フェイルセーフ（失敗時のフォールバック）が組み込まれています。バックテスト時のルックアヘッドバイアス防止も各モジュール設計で考慮されています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl（差分取得・保存）
  - J-Quants クライアント（fetch / save の一貫実装、認証トークン管理、レート制御、リトライ）
  - ニュース収集（RSS の正規化、SSRF 対策、前処理、raw_news への保存）
  - カレンダー管理（営業日判定・次営業日・前営業日取得・カレンダー更新ジョブ）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（監査用テーブル群とインデックスの作成）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（news_nlp.score_news: 銘柄ごとに OpenAI でセンチメントスコアを作成して ai_scores に保存）
  - 市場レジーム判定（regime_detector.score_regime: ETF MA + マクロ記事センチメントを合成）
- research
  - ファクター計算（momentum/value/volatility）および特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出ロジック付き）と Settings クラスでのアクセス

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや union 型の使用に基づく）
- DuckDB、OpenAI の Python SDK、defusedxml などが必要です。

1. リポジトリをクローンし、パッケージをインストール（例: editable install）
   - pip を使う場合:
     - python -m pip install -e . 
     - （プロジェクトに pyproject.toml / setup.cfg がある想定です）
2. 必要パッケージ例（プロジェクトの packaging に従ってください）
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリ以外の依存がある場合は pyproject / requirements を参照してください
   例:
     python -m pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 最小必須変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - OPENAI_API_KEY=your_openai_api_key
   - 省略可能（デフォルトが使用されるもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

4. DB 用ディレクトリ作成
   - デフォルトで data/ 以下に DB ファイルを作る想定のため必要に応じて作成:
     mkdir -p data

注意:
- .env のパースは POSIX シェル風の書式（export 対応、クォート、コメント処理など）に準拠しています。
- 自動読み込みはプロジェクトルートを __file__ から探索して行うため、パッケージを配布した後も正しく動作します。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから利用する際の簡単な例です。duckdb の接続オブジェクトを渡して機能を呼び出します。

1) ETL（日次パイプライン）を実行してデータを取得・保存する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（指定日分の銘柄別スコア）を取得して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY は環境変数でも可
print(f"scored {count} codes")
```

3) 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB を初期化する（別ファイルで監査専用に運用したい場合）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
# audit テーブル群が作成されます
```

5) カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 1, 2)))
print(next_trading_day(conn, date(2026, 1, 2)))
```

注意点:
- OpenAI 呼び出しの際は API キーが必要です（api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定）。
- J-Quants の API も認証が必要です（JQUANTS_REFRESH_TOKEN を .env などで設定）。jquants_client.get_id_token() がリフレッシュトークンを使って id_token を取得します。
- DuckDB 操作はトランザクション制御を行っている箇所があるため、既存トランザクションとの組み合わせに注意してください（audit.init_audit_schema の transactional オプション等）。

---

## .env（例）

プロジェクトルートに配置する .env の最小例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# 動作環境 / ログレベル
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 開発／テストに関するメモ

- 自動環境変数読み込みは .env/.env.local をプロジェクトルートから読み込みます。テストで独自に環境変数を注入したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI など外部 API 呼び出しは各モジュールでプライベートな _call_openai_api をラップしているため、ユニットテスト時は該当関数を patch / mock して応答を差し替える設計になっています（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- jquants_client._request は HTTP リトライ・401 自動リフレッシュ・レート制御を実装しているため、テストでは HTTP レスポンスをモックしてください。

---

## ディレクトリ構成（概要）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数設定・自動 .env ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント / 保存関数
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS 収集 / 前処理 / 保存
    - calendar_management.py       — マーケットカレンダー管理（営業日判定等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー等

---

## 補足（設計上のポイント）

- ルックアヘッドバイアス防止: 多くの関数は内部で datetime.today() / date.today() を直接参照せず、常に caller が target_date を渡す設計になっています。
- 冪等性: DB への保存関数は ON CONFLICT DO UPDATE や INSERT ... ON CONFLICT により冪等化されています。
- フェイルセーフ: 外部 API の失敗は可能な限り影響を局所化（スコアを 0 としてフォールバックする等）して、パイプライン全体の中断を防ぎます。
- セキュリティ: RSS 取得では SSRF 対策・受信サイズ制限・defusedxml による XML パース防御等を行っています。

---

必要であれば、README を実際のセットアップ手順（pyproject.toml / requirements.txt に合わせたインストール例）、運用時の具体的な cron / systemd ユニット例、より詳細な API 使用例（J-Quants / kabu ステーション / Slack 統合）などに拡張できます。どの情報を追加したいか教えてください。