# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなど、量的投資システムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に特化したデータ基盤および研究／運用ユーティリティ群です。主な目的は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への差分保存（ETL）
- ニュース記事の収集と OpenAI を用いた銘柄別センチメント評価（ニュースNLP）
- ETF とマクロニュースを組み合わせた市場レジーム判定（regime detector）
- ファクター（モメンタム／バリュー／ボラティリティ等）計算と特徴量探索
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針としては、Look-ahead バイアス回避、冪等性（Idempotency）、API レート管理、フェイルセーフ（API失敗時に続行）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py：J-Quants API クライアント（取得＋DuckDB保存）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミッター、リトライ、トークン自動リフレッシュ実装
- data/pipeline.py：日次 ETL パイプライン（run_daily_etl 等）と ETLResult
- data/news_collector.py：RSS 収集、前処理、raw_news 保存（SSRF 対策等）
- data/calendar_management.py：JPX カレンダー管理・営業日判定ユーティリティ
- data/quality.py：データ品質チェック（欠損・重複・スパイク・日付整合性）
- data/audit.py：監査ログ（signal_events / order_requests / executions）スキーマ初期化
- research/*：ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴抽出（forward returns、IC、summary）
- ai/news_nlp.py：ニュースをまとめて OpenAI に渡し、銘柄別スコアを ai_scores に書き込む（score_news）
- ai/regime_detector.py：ETF（1321）のMA乖離とマクロニュース（LLM）を合成して市場レジーム判定（score_regime）
- config.py：環境変数管理（.env 自動読み込み、必須変数チェック、settings オブジェクト）

---

## 要求環境

- Python 3.10+
- 必須 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外の依存は上記を想定してください。実際のプロジェクトでは requirements.txt / pyproject.toml で管理してください。

---

## セットアップ手順

1. リポジトリをクローン／配置し、プロジェクトルートに移動します。
2. 仮想環境を作成・有効化（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール:
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクト配布方法に応じて:
   # pip install -e .
   ```
4. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただしテスト時など自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）

任意（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（値が存在すれば無効）

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

※ 各関数は DuckDB 接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取ります。バックテストや運用は接続管理を適切に行ってください。

1) 日次 ETL を実行する例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア（OpenAI）を実行する例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている場合は api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定を実行する例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算（研究用）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

5) 監査ログ用データベース初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

---

## 自動 .env ロードの挙動

- config.py はパッケージルート（.git または pyproject.toml がある親ディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストや CI で便利です）。

---

## ディレクトリ構成

プロジェクトの主要ファイル／ディレクトリ（src/kabusys 配下）:

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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他データ関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージはファクター計算・特徴量解析を提供します。
- data パッケージは ETL、データ品質、ニュース収集、監査ログ等を含みます。
- ai パッケージは OpenAI を用いた NLP 処理とレジーム判定を含みます。

---

## 運用上の注意

- OpenAI（gpt-4o-mini）をコールする箇所は API 利用料が発生します。テストはモックで行ってください（score_news / _call_openai_api を patch）。
- J-Quants API はレート制限があり、jquants_client で制御していますが、並列実行時は注意してください。
- DuckDB の executemany は一部バージョンで空リストを受け付けない処理があるため、空チェックを行ってから実行しています。
- データ品質チェック（data.quality）で検出された問題は ETL を止めずに報告します。重大度に応じて呼び出し側で対応してください。
- 監査ログは削除しない前提です。初期化後はトレーサビリティを保てるように発注ID等を UUID で管理してください。

---

## 貢献・拡張

- 新しいデータソースの追加（RSS ソース拡張、API エンドポイントの追加）
- 研究モジュールに新ファクター追加やパフォーマンス最適化
- モデルのプロンプト改善、OpenAI 呼び出しのバッチ戦略の調整
- テストカバレッジ強化（外部 API をモックするユーティリティの整備）

---

ご不明点や README に加えるべき具体的な使い方・例（CI 設定、デプロイ手順、cron ジョブ例など）があればお知らせください。必要に応じて README を拡張します。