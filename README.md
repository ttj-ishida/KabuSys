# KabuSys

日本株向け自動売買／データ基盤ライブラリ (KabuSys)。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を利用したセンチメント）、研究用ファクター計算、監査ログ（約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダーなどの差分 ETL と DuckDB への保存（冪等性あり）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析／マクロセンチメントによる市場レジーム判定
- 研究（research）向けのファクター計算・特徴量評価ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ

このパッケージは、バックテストや運用バッチ処理の基盤となることを想定して設計されています。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レートリミット・リトライ）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・前処理・記事ID生成・SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime）：ETF(1321) の MA200 乖離とマクロニュースを合成
  - ニュース NLP ユーティリティ（プロンプト設計・バッチ処理・JSON Mode 対応）
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

---

## セットアップ手順

前提:
- Python 3.9+（型注釈の union 表記などを参照）
- DuckDB 等ネイティブ拡張が必要なライブラリのビルド環境

1. リポジトリをクローンしてパッケージをインストール
   - 開発時:
     - pip install -e . もしくは poetry / flit 等を利用
2. 必要なパッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - これらを requirements.txt または pyproject.toml からインストールしてください。
   例:
   ```
   pip install duckdb openai defusedxml
   ```
3. 環境変数 / .env ファイルを用意
   - 自動でプロジェクトルートの `.env` / `.env.local` が読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を設定するか、score_news / score_regime 実行時に api_key を渡してください。
   - 任意:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用データベース、デフォルト: data/monitoring.db）
     - KABUSYS_ENV：development / paper_trading / live
     - LOG_LEVEL：DEBUG/INFO/...
4. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下は Python からの呼び出し例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを当日（ターゲット日）分スコア化する
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY 環境変数が設定されていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム（マクロ + MA200）をスコアリングして保存する
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って order_requests 等を記録できます
```

- 研究ユーティリティの使用例（モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
z_records = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- score_news / score_regime 等は OpenAI API を呼び出すため、API キーと課金設定に注意してください（テスト時はモック推奨）。
- ETL は J-Quants API 呼び出しを行います。J-Quants の利用制限（レートや権限）に注意してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack 通知先
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（監視用、default: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

.env.example（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（fetch / save）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - quality.py          — データ品質チェック
  - audit.py            — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py  — Momentum / Volatility / Value 等
  - feature_exploration.py — 将来リターン / IC / サマリー
- research の公開ユーティリティに data.stats の zscore_normalize を参照

---

## 開発・テストのヒント

- OpenAI / J-Quants の外部 API 呼び出し部分はモックしやすいよう設計されています（テスト時は内部の _call_openai_api や network 関数を patch してください）。
- ETL の差分処理は最大バックフィル日数や calendar lookahead 等で動作を調整できます。
- DuckDB への executemany に空リストを渡せないケース（特定バージョン）を考慮した実装になっています。テストで空リストが発生するパスを確認してください。
- news_collector は SSRF / gzip bomb 等の脅威を考慮した堅牢な設計になっています。実運用でソース追加する際は URL 検証ロジックに留意してください。

---

もし README に加えたいサンプル .env.example や、CI/デプロイ手順、単体テスト実行方法など具体的な追記希望があれば教えてください。補足ドキュメントを作成します。