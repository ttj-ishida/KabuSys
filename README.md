# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このプロジェクトは、J-Quants や RSS／OpenAI を利用してデータを収集・品質検査・特徴量生成し、戦略・発注・監視のためのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS によるニュース収集と OpenAI を使ったニュースセンチメント自動スコアリング
- マーケットレジーム判定（ETF MA とマクロニュースの合成スコア）
- ファクター計算・特徴量探索・統計ユーティリティ（研究用）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を記録するスキーマ初期化ユーティリティ
- データ品質チェック、マーケットカレンダー管理などの基盤機能

ライブラリは DuckDB を主要な永続層として想定し、OpenAI（gpt-4o-mini）での JSON Mode を使った静的スコアリングを行います。自動売買の本体（注文送信ロジック等）は別モジュール/アプリで利用できるように設計されています。

---

## 主な機能一覧

- 環境変数読み込み・管理（.env / .env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 差分取得（ページネーション対応）
  - レート制御、401 自動リフレッシュ、再試行ロジック
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- マーケットカレンダー管理（営業日判定、前後の営業日取得）
- ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、IC / rank / zscore 正規化）
- 監査スキーマ初期化（signal_events / order_requests / executions とインデックス）
- 監視設定（PID ファイル、リソースしきい値等を環境変数で設定）

---

## 必要な環境変数

主に以下を想定しています（README に記載の他、コード内 Settings クラスに全項目あり）。

必須（少なくとも実行する機能に応じてセットしてください）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN : Slack 通知を使う場合
- SLACK_CHANNEL_ID : Slack のチャンネル ID（通知先）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注連携がある場合）

オプション（デフォルトあり）:

- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (=1 にするとプロジェクトルートの .env 自動ロードを無効化)

ヒント: プロジェクトルートに .env.example を置き、そこから .env を作成する想定です（Settings._require は未設定時に ValueError を出します）。

---

## セットアップ手順（ローカル実行向け）

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate あるいは Windows なら .venv\Scripts\activate

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r requirements.txt / pip install -e . を推奨します。

3. 環境変数（.env）を作成
   - プロジェクトルートに .env を作成し、必須の環境変数を設定します。
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

   自動読み込みはデフォルトで有効です。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

4. データベース初期化（監査用 DuckDB など）
   - Python 上で kabusys.data.audit.init_audit_db を呼び出してファイル作成・スキーマ初期化が可能です。

---

## 使い方（簡単な例）

以下はライブラリ API の代表例です。実行は仮想環境で行ってください。

- DuckDB 接続を作成して日次 ETL を走らせる

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースをスコアリングして ai_scores テーブルに書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込み件数:", n_written)

- 市場レジームを判定して market_regime テーブルへ書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査データベースの初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

注意点:
- AI 呼び出し（OpenAI）は API キーのレートやコストに注意してください。
- 日付処理はルックアヘッドバイアス対策で target_date を明示的に渡す設計です。内部で date.today() を参照しない関数が多くあります（テスト・バックテスト対応）。

---

## 自動環境読み込みの挙動

- パッケージ起動時（kabusys.config）にプロジェクトルートを .git または pyproject.toml で探索し、見つかった場合は以下順で .env を読み込みます:
  1. OS 環境変数（既存の環境変数を保護）
  2. .env（上書きしない）
  3. .env.local（既存の OS 環境変数を保護しつつ上書き）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースは一般的なシンタックス（export を含む）やクォート、コメント行に対応しています。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール構成（src/kabusys 以下）です。提供済みファイルに基づく抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save 系）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL インターフェース再エクスポート
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - quality.py                 — データ品質チェック
    - calendar_management.py     — 市場カレンダー管理（営業日判定等）
    - audit.py                   — 監査ログスキーマ初期化
    - news_collector.py          — RSS ニュース収集（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum / value / volatility）
    - feature_exploration.py     — forward returns / IC / rank / summary
  - ai/、research/ と data/ はそれぞれ独立したユーティリティ群として設計されています。

（その他、strategy / execution / monitoring といった名前のサブパッケージが __init__ に示唆されていますが、ここに示したファイル群が主要な実装です）

---

## 開発・テスト時の補足

- テストでは外部 API（OpenAI / J-Quants / 外部 RSS）呼び出しをモックして利用することを想定しています。モジュール内の _call_openai_api や _urlopen、J-Quants のトークン取得等は patch して差し替え可能です。
- DuckDB はファイルベースでも :memory: を使ったインメモリでも利用できます（kabusys.data.audit.init_audit_db などは ":memory:" を受けます）。
- ETL 実行はログと品質チェックの結果（ETLResult）を返します。品質問題をどうハンドリングするかは呼び出し側で判断してください（Fail-Fast にはしていません）。

---

## ライセンス / 貢献

この README はコードベースの説明を目的としています。実際のリポジトリには LICENSE や CONTRIBUTING ガイドを追加してください。

---

不明点や README に追記したい利用シナリオ（例: バックテスト連携、kabu ステーション連携手順、Slack 通知の設定例など）があれば教えてください。必要に応じてサンプル .env.example や簡単な起動スクリプト例も追加します。