# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants、kabuステーション、OpenAI（LLM）などを連携し、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログを提供します。

## 概要
- DuckDB をデータストアとして用いるデータプラットフォームと、取引ロジックに必要なユーティリティ群を収めた Python パッケージ。
- ETL（市場カレンダー、株価、財務）と品質チェック、ニュース収集＋LLMベースの銘柄センチメント算出、ETF を用いた市場レジーム判定、リサーチ（ファクター計算・IC 等）、監査ログスキーマの初期化/管理などを実装。
- OpenAI（gpt-4o-mini 等）を用いてニュースセンチメントやマクロセンチメントを算出し、ai_scores / market_regime などのテーブルへ書き込みます。
- J-Quants API クライアントを内蔵し、API レート管理・リトライ・トークンリフレッシュ・ページネーションに対応。

## 主な機能一覧
- ETL（差分取得／バックフィル／保存）:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック:
  - 欠損、重複、スパイク、将来日付／非営業日データの検出（quality.run_all_checks）
- ニュース収集:
  - RSS フィード取得、防御的パース、トラッキングパラメータ除去、raw_news への冪等保存（news_collector）
- ニュース NLP / LLM スコアリング:
  - score_news: 銘柄ごとのセンチメントスコアを生成して ai_scores へ保存
  - モデル呼び出しにリトライ・バリデーションを実装
- 市場レジーム判定:
  - score_regime: ETF(1321) の 200日MA乖離 + マクロニュースセンチメントの合成で daily market_regime を作成
- 研究用ユーティリティ:
  - ファクター計算（momentum, volatility, value）、forward returns、IC、統計サマリ、Z-score 正規化
- J-Quants クライアント:
  - fetch / save の一貫処理（ページネーション、rate limit、token refresh）
- 監査ログ（audit）:
  - signal_events / order_requests / executions など監査テーブルの DDL と初期化関数（init_audit_schema / init_audit_db）
- 環境設定管理:
  - .env 自動読み込み（プロジェクトルート検出）・必須環境変数の明示（config.Settings）

## 必要条件
- Python 3.10+
- 主な依存パッケージ（コード中からの推奨）:
  - duckdb
  - openai (OpenAI Python SDK v)
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / RSS フィード 等

（依存バージョンはプロジェクトの pyproject.toml / requirements.txt を参照してください）

## インストール
開発環境でソースを使う例:
```
git clone <repo-url>
cd <repo-root>
pip install -e .  # または pip install -r requirements.txt
```

## 環境変数（主なもの）
KabuSys は .env/.env.local または OS 環境変数から設定を読み込みます（自動ロードはプロジェクトルートに .git または pyproject.toml がある場合のみ）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID
- KABU_API_PASSWORD: kabuステーション API パスワード

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に渡すことも可）

例 .env:
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
KABU_API_PASSWORD=...
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
```

## セットアップ手順（初期化例）
1. 依存パッケージをインストール
2. .env を作成して環境変数を設定
3. DuckDB スキーマ（必要なテーブル）を準備する（本リポジトリに schema 初期化の関数があれば利用）
4. 監査ログ用 DB を初期化する例:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn をさらに使って監査テーブルへアクセス可能
```

## 使い方（代表的な例）
- 日次 ETL を実行して株価・財務・カレンダーを取得・保存する:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存する:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数
print("written:", n_written)
```

- 市場レジーム判定:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマの初期化（既存接続へ適用）:
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

## ディレクトリ構成（主なファイル）
※このリポジトリの src/kabusys 配下を抜粋

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                # ニュース NLP（score_news 等）
    - regime_detector.py        # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（fetch/save）
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - etl.py                    # ETLResult 再エクスポート
    - quality.py                # データ品質チェック
    - news_collector.py         # RSS ニュース収集
    - calendar_management.py    # 市場カレンダー管理（is_trading_day 等）
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - audit.py                  # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py        # ファクター計算（momentum/value/volatility）
    - feature_exploration.py    # forward returns, IC, summary, rank

## 開発ノート / テスト時の注意点
- LLM / ネットワーク呼び出しは外部依存のため、テストでは各モジュール内部の _call_openai_api や network 関数を patch/mocking する想定です（news_nlp, regime_detector に相互に独立した _call_openai_api 実装がある点に注目）。
- config モジュールはプロジェクトルート（.git / pyproject.toml）を探索して .env/.env.local を自動で読み込みます。テストで自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、空パラメータのケースはコード側でガードされています。
- J-Quants クライアントは内部で固定間隔の RateLimiter を用いているため、短時間に大量リクエストする場合は注意してください。

## ロギング
- 設定は環境変数 LOG_LEVEL（DEBUG/INFO/...）で制御。
- 重要な操作や失敗は logger に記録されます（各モジュールで logger = logging.getLogger(__name__) を使用）。

---

この README はコードの主要機能と使用方法の要点をまとめたものです。より詳しい設計情報（DataPlatform.md / StrategyModel.md 等）がリポジトリ内にある場合はそちらも参照してください。質問や追加で載せてほしい使用例があれば教えてください。