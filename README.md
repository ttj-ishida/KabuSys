# KabuSys

日本株向けの自動売買 / データパイプラインライブラリです。  
DuckDB を用いたデータプラットフォーム（ETL・品質チェック・カレンダー管理）と、
OpenAI を利用したニュース NLP / 市場レジーム判定、監査ログ（発注→約定トレーサビリティ）等を備えます。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と、OpenAI（gpt-4o-mini）を使った銘柄別センチメント評価（ai_scores）
- マクロニュース × ETF（1321）MA200乖離を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム/バリュー/ボラティリティ等）と統計ユーティリティ
- 発注〜約定までをトレースする監査ログスキーマ（DuckDB）と初期化ユーティリティ

主要設計方針として「ルックアヘッドバイアスの防止」「冪等性」「フェイルセーフ（API失敗時の継続）」を意識しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証自動リフレッシュ・レート制御）
  - カレンダー管理（市場営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news, SSRF・gzip・サイズ対策済み）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime：マクロセンチメントとETF MA乖離で market_regime を算出
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - Settings クラス：環境変数から設定を読み込む（.env/.env.local 自動ロード機能あり）
- その他
  - DuckDB をデフォルト DB として使用
  - OpenAI（gpt-4o-mini）の JSON Mode を使用（API キーは引数または環境変数で指定）

---

## セットアップ手順

1. Python 環境を準備（推奨: pyenv/venv）
   - Python 3.9+ を想定しています（お使いの環境に合わせてください）。

2. パッケージをインストール
   - ソースルートで（パッケージ化されている想定）:
     - pip install -e .
   - 必要に応じて明示的に主な依存を入れる例:
     - pip install duckdb openai defusedxml

   （本リポジトリに requirements.txt があればそれを使ってください）

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（本プロジェクトの一部モジュールで使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を呼ぶ場合。関数引数で注入可能）

参考の .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

デフォルト DB パス:
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring 用): data/monitoring.db

---

## 使い方（簡易ガイド）

以下は主要なユースケースの例です。各関数はモジュールから直接呼べます。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,29))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,29), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,29), api_key=None)
```

- 監査ログ DB を初期化（新規ファイル）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続
```

- RSS 取得の実行例（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI 呼び出しを伴う処理は API コストが発生します。ローカルでテストする場合は api_key をモックする、もしくは OPENAI_API_KEY を設定してください。
- AI 呼出しは失敗時にフォールバック（0.0 等）する実装になっていますが、ログを確認してください。

---

## 主な API / 実行エントリ

- data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次の ETL（カレンダー → 株価 → 財務 → 品質チェック）
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
  - 個別 ETL ジョブ
- data.jquants_client.fetch_* / save_* 系
  - J-Quants API 経由の取得/保存ユーティリティ
- data.calendar_update_job(conn, lookahead_days=...)
  - カレンダー差分更新ジョブ
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 銘柄別ニュースセンチメント算出・保存
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム判定・保存
- data.audit.init_audit_db(path) / init_audit_schema(conn)
  - 監査ログの初期化

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主要ファイル/ディレクトリと役割です（抜粋）。

- kabusys/
  - __init__.py — パッケージエントリ（version等）
  - config.py — 環境変数・設定読み込み（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py — RSS 収集（SSRF/サイズ/解析対策）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義と初期化（信頼性を重視）
    - etl.py — ETL 公開インターフェース（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - research/*（研究用ユーティリティ）
  - その他モジュール多数（上記は主なもの）

---

## ログ / 設定

- 環境変数 `LOG_LEVEL` でログレベルを指定（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルトは INFO。
- `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれか。設定ミスは例外を投げます。
- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。テスト時に自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## テスト・開発時のヒント

- AI を呼ぶ箇所（news_nlp/regime_detector）は内部で OpenAI クライアント呼び出しを行います。ユニットテストでは該当関数（モジュール）内の _call_openai_api を patch / mock してテストしてください（実装が想定済み）。
- news_collector のネットワーク部分は _urlopen をモックすることで外部通信を避けられます。
- DuckDB による一部 executemany の挙動や型の制約（空リスト不可等）に注意してテストデータを作成してください。

---

## 免責 / 注意事項

- 実際の売買・発注ロジック（execution / broker 連携）はこのコードベースの一部にある想定ですが、資金が絡む運用は慎重に行ってください。本リポジトリは研究・開発を目的としたライブラリであり、実運用に際しては十分な検証と監査が必要です。
- OpenAI / J-Quants / 証券会社 API の利用にはそれぞれの利用規約と課金ルールが適用されます。API キーの管理には注意してください。

---

必要であれば README に「コマンド例」「より詳細な .env.example」「開発ワークフロー（テスト・CI）」などを追記します。どの情報を追加しますか？