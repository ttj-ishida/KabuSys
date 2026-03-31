# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算、ニュース NLP（OpenAI）や市場レジーム判定、監査ログ（約定トレーサビリティ）などの機能を提供します。

README は日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データ基盤を構築するための内部ライブラリです。主な目的は以下です：

- J-Quants API からの株価・財務・市場カレンダーの差分取得と DuckDB への保存（ETL）
- RSS からのニュース収集と raw_news への保存、銘柄紐付け
- OpenAI を用いたニュースセンチメント解析（ai.score_news）と市場レジーム判定（ai.score_regime）
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算と特徴量解析（research）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定フローの監査ログ用スキーマ（audit）と初期化ユーティリティ

設計では「ルックアヘッドバイアス回避」「冪等性」「外部API／ネットワークリトライ」「DuckDB ベースの効率的な処理」を重視しています。

---

## 機能一覧

主な機能（抜粋）：

- data/
  - jquants_client: J-Quants API 呼び出し、取得データの DuckDB 保存（差分取得、ページネーション、トークン管理、レート制御、リトライ）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・SSRF 対策・正規化
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて OpenAI でセンチメント評価 → ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA とニュースマクロセンチメントを合成して market_regime を作成
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数の読み込み（.env / .env.local 自動読み込み）、Settings クラス（必須設定の取得）
- audit
  - init_audit_schema / init_audit_db：監査テーブルの初期化

---

## セットアップ手順

前提
- Python 3.10 以上推奨（型注釈に | を使用）
- DuckDB を利用（Python パッケージ `duckdb`）
- OpenAI API を使用する機能は `openai` パッケージ（最新版 SDK）を必要とします
- RSS パースに `defusedxml` を利用

例: 必要なパッケージ（プロジェクトに requirements.txt がない場合は手動で）
pip install duckdb openai defusedxml

1. リポジトリをクローン／配置
2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml
   （追加で logging 設定や unittest.mock を使う場合は標準ライブラリで足ります）
4. 環境変数を設定
   - 自動でプロジェクトルート（.git や pyproject.toml）を探し `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client 用）
- SLACK_BOT_TOKEN: Slack 通知（該当機能利用時）
- SLACK_CHANNEL_ID: Slack チャンネル ID（該当機能利用時）
- KABU_API_PASSWORD: kabu API パスワード（kabu 連携機能利用時）
- OPENAI_API_KEY: OpenAI を使用する場合（ai.score_news / ai.score_regime）

その他オプション
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（設定が正しくないと例外）

設定は .env に書くか OS 環境変数としてエクスポートしてください。.env のパースは Bash 風の形式（export を許容、クォートの解釈、コメント処理など）に対応しています。

---

## 使い方（よく使う例）

以下は Python REPL / スクリプト からの利用例です。

1) DuckDB 接続を用意して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 今日の ETL（target_date を明示的に渡しても良い）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定しておく
print("scored:", count)
```

3) 市場レジーム判定（regime）を実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキーは環境変数 OPENAI_API_KEY でも可
```

4) 監査用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / executions テーブルへアクセスできます
```

5) RSS を取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点
- ai モジュール（news_nlp, regime_detector）は OpenAI の Chat Completions（JSON mode）を使用します。API呼び出しはリトライやフェイルセーフを備えていますが、APIキーは必ず設定してください。
- J-Quants API 呼び出しはレート制御・トークンリフレッシュを行います。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- ETL / データ修正を行う際のトランザクションや ROLLBACK の扱いは各関数内部で適切に行われますが、運用スクリプトでのエラーハンドリングを併用してください。

---

## 自動環境変数読み込み

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動で読み込みます（`.env.local` は上書き）。
- テストや CI で自動読み込みを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1

読み込みポリシー
- OS環境変数 > .env.local > .env の順で優先度
- 既存の OS 環境変数は上書きされません（.env.local による上書きは可能）

---

## ディレクトリ構成（主要ファイル説明）

（パッケージルート: src/kabusys 以下）

- __init__.py
  - パッケージのバージョンと公開モジュール設定

- config.py
  - 環境変数の自動読み込み、Settings クラス（必須設定の検証と取得）

- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄ごとにまとめ、OpenAI でセンチメントを算出して ai_scores テーブルへ保存するロジック
  - regime_detector.py: ETF (1321) の MA とニュースマクロセンチメントを合成して market_regime を書き込む

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存のユーティリティ）
  - pipeline.py: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得・前処理・ID 正規化・SSRF 対策
  - calendar_management.py: market_calendar 管理と営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ（DDL/インデックス）定義、init_audit_schema/init_audit_db

- research/
  - __init__.py
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank

その他
- 多くの関数は duckdb.DuckDBPyConnection を受け取り SQL を直接実行しています。DB スキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）は別途スキーマ定義／初期化を行う必要があります（ETL や audit.init_audit_schema 等で一部のテーブルは初期化できます）。

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス対策として、本ライブラリの多くの関数は target_date を明示的に受け取り、内部で datetime.now() や date.today() を不用意に参照しないよう設計されています。バックテスト用途でも target_date を明示的に渡してください。
- OpenAI 呼び出し・J-Quants 呼び出しはいずれもリトライ・バックオフを組み込んでいますが、API 利用料／レート制限に注意して運用してください。
- ETL の部分失敗に備え、run_daily_etl は部分的なエラー情報を ETLResult に集約します。運用スクリプト側で ETLResult を監視し、必要に応じてアラート／再実行を行ってください。
- news_collector では SSRF 対策（リダイレクト先検査、プライベートホスト拒否）や最大受信サイズチェックを実装しています。外部 RSS を登録する際はメディアの信頼性を検討してください。

---

## 参考 / 連絡

この README はライブラリの主要機能と使い方を簡潔にまとめたものです。各モジュール内には詳細な docstring と設計方針が記載されていますので、実装を利用・変更する場合は該当モジュールのソースを参照してください。

不明点や追加ドキュメントの要望があれば教えてください。