# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集と LLM によるニュースセンチメント評価、ファクター計算・リサーチユーティリティ、監査ログ（発注／約定トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を直接参照しない設計）
- DuckDB をデータ格納・集計基盤として利用
- 外部 API 呼び出しは再試行・バックオフ・フェイルセーフを備える
- DB 操作は冪等（ON CONFLICT 等）を重視

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数の自動マージ（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）
- データ取得・ETL（jquants_client + pipeline）
  - 株価日足（OHLCV）、財務データ（四半期）、JPX カレンダー等の差分取得・保存
  - run_daily_etl による日次 ETL（品質チェック含む）
- ニュース収集（RSS）と NLP
  - RSS 取得・前処理（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント score_news
  - マクロニュースと ETF (1321) の MA200 乖離で市場レジーム判定 score_regime
- リサーチ系ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計要約
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマと初期化（冪等）
  - 監査用 DuckDB DB の初期化ユーティリティ

---

## 必要条件（主な依存）

- Python 3.10+（型アノテーションに Path | None 等を利用）
- パッケージ依存例（プロジェクトの pyproject.toml / requirements を参照してください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を多用）
- J-Quants API アクセス（リフレッシュトークン）、OpenAI API キー 等の外部資格情報

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e . 
   - または必要な依存を個別に pip install duckdb openai defusedxml など

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を配置すると自動読み込みされます。
   - 必須環境変数（コード中で _require() によって要求されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（必要な場合）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（使用する場合）
     - SLACK_CHANNEL_ID — Slack チャンネルID（使用する場合）
   - 任意/デフォルト:
     - KABUSYS_ENV = development | paper_trading | live（default: development）
     - LOG_LEVEL = DEBUG | INFO | ...
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB, default data/monitoring.db）
     - OPENAI_API_KEY は score_news/score_regime 呼出しで引数に渡すことも可
   - テスト時に自動 .env ロードを抑止する:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要なユースケース例）

※ 以下は Python インタプリタ／スクリプト内での利用例です。日時は date を明示的に渡し、ルックアヘッドを防ぎます。

- DuckDB 接続をつくる
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())  # ETLResult の概要確認

- ニュースのセンチメントを計算して ai_scores に書き込む
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  - print("scored:", n)

- 市場レジーム判定（ETF 1321 + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- 監査ログ用 DB を初期化してスキーマを作る
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # audit_conn に対して order/signals/exec ログを保存できる

- ファクター計算・リサーチ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from datetime import date
  - mom = calc_momentum(conn, date(2026, 3, 20))
  - vol = calc_volatility(conn, date(2026, 3, 20))
  - val = calc_value(conn, date(2026, 3, 20))

- 補助ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

注意点：
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL/保存処理は DuckDB のテーブルスキーマ（raw_prices 等）を前提としているため、初期スキーマの作成は別途スキーマ定義モジュール（project 側）で行ってください。

---

## .env の例（参考）

以下は必要なキーの例です（ファイル名: .env）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
OPENAI_API_KEY=sk-...

ログレベル等は任意で設定できます：
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント評価（score_news）
  - regime_detector.py     — ETF MA200 + マクロセンチメントで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得 / DuckDB 保存）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の公開再エクスポート
  - news_collector.py      — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - quality.py             — データ品質チェック（欠損・スパイク・重複等）
  - stats.py               — 統計ユーティリティ（zscore_normalize 等）
  - audit.py               — 監査ログスキーマ初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py     — Momentum/Value/Volatility 等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー 等
- research/__init__.py
- その他（execution / monitoring 等のパッケージエクスポートは __all__ に含む）

---

## 開発・運用のヒント

- 環境設定は settings（kabusys.config.settings）経由で参照できます。必須項目は _require() により ValueError を出すため、起動前に .env を整備してください。
- DuckDB ファイルはデフォルト data/kabusys.duckdb。テスト時は ":memory:" を使うことも可能。
- OpenAI 呼び出しは内部でリトライや JSON バリデーションを行いますが、アカウントのレートや費用に注意してください。
- ETL は個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）を組み合わせているため、部分的に実行して挙動を確認できます。
- news_collector は SSRF 対策・受信サイズ制限・トラッキング除去等に対応しています。RSS ソースの追加は DEFAULT_RSS_SOURCES を参考に拡張してください。

---

この README はコードベースから主要機能と利用手順をまとめたものです。実運用時は pyproject.toml / requirements ファイル、及びプロジェクト固有の運用手順書（デプロイ手順・監視設定・バックアップ方針等）を必ず参照してください。質問や追加のドキュメント化（API リファレンス、スキーマ定義、運用 Runbook 等）が必要であれば教えてください。