# KabuSys

KabuSys は日本株の自動売買・データプラットフォームのコアライブラリ群です。  
J-Quants API や RSS を利用したデータ収集（ETL）、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、バックテスト・オペレーション・研究用途に必要な機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を安易に参照しない）
- DuckDB を中心としたローカルデータ管理
- 冪等性・フェイルセーフを重視した ETL と永続化
- 外部 API 呼び出しに対するリトライ・レート制御・安全対策を実装

---

## 機能一覧（抜粋）

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場情報）
  - 差分更新・バックフィルを行う日次 ETL パイプライン（run_daily_etl 等）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合のチェック（quality モジュール）
- カレンダー管理
  - JPX カレンダーの保持、営業日判定・前後営業日の取得（calendar_management）
- ニュース収集・前処理
  - RSS 取得・前処理・raw_news / news_symbols への保存（news_collector）
  - SSRF / gzip / XML 注入対策等の安全実装
- AI（OpenAI）連携
  - ニュースの銘柄別センチメントスコア生成（news_nlp.score_news）
  - マクロセンチメント + 指標の合成による市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しはリトライや JSON モードを利用した堅牢な実装
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research モジュール）
  - 将来リターン計算、IC 計算、統計サマリー等
- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査テーブルの DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env / 環境変数の自動読み込み、必須キーの検証（config）

---

## 前提・依存関係

- Python 3.10+
- 主な Python パッケージ（プロジェクトに requirements.txt がない場合は下記をインストールしてください）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, datetime, logging, json, hashlib 等

（実行環境によって追加の依存がある可能性があります。パッケージ化された配布があればそちらの指示に従ってください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用）

4. 環境変数を準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。自動読み込みはデフォルトで有効です（config モジュールが .git または pyproject.toml を起点に探索してロードします）。
   - 最低限必要な環境変数（config.Settings で必須扱いのもの）：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意／推奨：
     - OPENAI_API_KEY（score_news / score_regime を使う場合）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...。デフォルト INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用途の SQLite、デフォルト data/monitoring.db）
     - KABU_API_BASE_URL（kabuステーション API のベースURL）
   - 自動 .env ロードを無効化したい場合：
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単なコード例）

下記は一例です。DuckDB 接続は `duckdb.connect(path)` を使用します。

- 日次 ETL を実行する（株価・財務・カレンダー取得＋品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを生成する（OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておく）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_scored = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_scored)
```

- 市場レジーム判定を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意点：
- OpenAI 呼び出しは外部 API を用いるため、テスト時は `kabusys.ai.news_nlp._call_openai_api` 等をモックすると良いです（コード内でその差し替えを想定した設計）。
- J-Quants API へのアクセスは認証トークンが必要です。get_id_token() は settings.jquants_refresh_token を利用します。

---

## よく使う API（モジュール・関数一覧）

- kabusys.config
  - settings: 環境変数ラッパー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）
- kabusys.data
  - pipeline.run_daily_etl(...)
  - etl.ETLResult
  - jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
  - news_collector.fetch_rss / preprocess_text
  - calendar_management.is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - quality.run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - audit.init_audit_schema / init_audit_db
- kabusys.ai
  - news_nlp.score_news
  - regime_detector.score_regime
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

（コードベースの src/kabusys を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - etl.py                   — ETL インターフェース再公開
    - pipeline.py              — 日次 ETL パイプライン（run_daily_etl 等）
    - jquants_client.py        — J-Quants API クライアント + DuckDB 保存
    - news_collector.py        — RSS 取得・前処理・保存
    - calendar_management.py   — マーケットカレンダー管理・営業日ロジック
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（z-score など）
    - audit.py                 — 監査ログテーブル定義・初期化
    - pipeline.py              — ETL パイプライン（ETLResult 等）
    - etl.py                   — 再エクスポート（ETLResult）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン、IC、統計サマリー
  - monitoring/                 — （監視・モニタリング用スクリプト等が入る想定）
  - strategy/                   — （戦略実装層：シグナル生成等を想定）
  - execution/                  — （発注・ブローカー接続を想定）

（実際のリポジトリには上記以外の補助ファイルや追加モジュールが存在する可能性があります）

---

## 運用上の注意

- API キーやシークレットは .env または環境変数で管理してください。リポジトリに直書きしないでください。
- OpenAI・J-Quants へのリクエストは課金やレート制限、プライバシー・セキュリティ上の配慮が必要です。実行前にキーや利用料を確認してください。
- DuckDB ファイルはバイナリ形式のローカル DB です。バックアップ・ローテーションを運用で検討してください。
- audit（監査ログ）は削除しない前提で設計されています。ストレージ計画を立ててください。

---

## テスト・開発ヒント

- OpenAI 呼び出しを行う箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）はテスト時に patch して外部呼び出しをモックできます。
- config の自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（ユニットテストで環境を操作する際に便利）。

---

この README はコードベース内のドキュメントコメント（docstring）と設計注釈をもとに作成しています。より詳細な運用手順や API シグネチャ、Schema 定義・マイグレーション、CI/CD・デプロイ方法はプロジェクトの別ドキュメント（Design docs / Operation docs）を参照してください。