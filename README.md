# KabuSys — 日本株自動売買プラットフォーム（README）

概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめた README です。

目次
- プロジェクト概要
- 主な機能
- 動作要件・依存ライブラリ
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）一覧
- ディレクトリ構成（主要ファイル）
- 補足 / 設計方針メモ

---

## プロジェクト概要
KabuSys は日本株のデータ収集（J-Quants/API）、データ品質チェック、特徴量（ファクター）計算、ニュースベースの AI スコアリング、マーケットレジーム判定、ETL パイプライン、監査（トレーサビリティ）テーブルなどを含む日本株自動売買プラットフォームのコアライブラリです。DuckDB をデータ層に採用し、OpenAI（gpt-4o-mini）を用いたニュース NLP によるセンチメント評価を組み合わせて、研究・実運用双方で利用できるモジュール群を提供します。

---

## 主な機能
- 環境設定管理（.env 自動読み込み、必須チェック）
- J-Quants API クライアント（株価・財務・市場カレンダー取得、認証 / リトライ / レート制御）
- ETL パイプライン（差分取得、保存、品質チェック、日次 ETL 実行）
- ニュース収集（RSS 取得・前処理・SSRF 対策、raw_news への保存想定）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ計算、将来リターン、IC 計算、Z-score 正規化）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal_events / order_requests / executions の DDL・初期化ユーティリティ）
- DuckDB への冪等保存（ON CONFLICT を利用）

---

## 動作要件・依存ライブラリ
- Python 3.10 以上（PEP 604 の `X | Y` 型などを利用）
- 必要な主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリ（urllib, json, datetime, logging 等）

（pip install 要件はプロジェクト配布時の requirements.txt / pyproject.toml を参照してください。ここでは代表的なライブラリ名のみ記載しています。）

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （配布されていれば）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成してください。
   - 自動読み込みはデフォルトで有効（`.env` / `.env.local` は config モジュールが自動で読み込みます）。
   - 自動読み込みを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベースディレクトリの作成（必要なら）
   - 例: mkdir -p data

---

## 簡単な使い方（コード例）
以下は最小限の使用例です。実行前に必要な環境変数（下記参照）を設定してください。

- DuckDB 接続を開いて日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP による銘柄スコア計算（OpenAI API キーは環境変数 OPENAI_API_KEY で指定可能）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数使用
  print("scored:", count)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  # market_regime テーブルへ書き込みが行われます
  ```

- 監査 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring.db")
  # audit テーブル群が作成されます
  ```

- 市場カレンダーユーティリティ:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))
  ```

- RSS 取得（ニュースコレクターの単体利用例）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src_name = "yahoo_finance"
  url = DEFAULT_RSS_SOURCES[src_name]
  articles = fetch_rss(url, source=src_name)
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

---

## 環境変数（主要）
config.Settings から参照される主要な環境変数（必須／デフォルト値付き）:

必須（未設定時はエラーを投げる）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系で必要）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
- KABUSYS_*.（他の専用設定がある場合は .env.example を参照）
- OPENAI_API_KEY — OpenAI API キー（AI 関連処理で使用；関数呼び出し時に api_key 引数でも指定可能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）パス（デフォルト: data/monitoring.db）

自動読み込み：
- パッケージ起点でプロジェクトルート (.git または pyproject.toml を探索) が見つかれば、.env を自動で読み込みます。さらに .env.local があればそちらで上書きします（ただし OS の環境変数は保護されます）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下を抜粋・要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py — 市場レジーム判定（1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
    - pipeline.py — ETL パイプライン実装（run_daily_etl 等）
    - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py — RSS 取得・前処理・保存ロジック
    - calendar_management.py — 市場カレンダー管理/営業日判定
    - quality.py — データ品質チェック（欠損・重複・スパイク等）
    - stats.py — 汎用統計（z-score 等）
    - audit.py — 監査ログ（DDL / 初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 補足 / 設計方針（抜粋）
- ルックアヘッドバイアス対策：多くのモジュールが date.today()/datetime.today() を直接参照せず、外部から target_date を注入して処理します（過去データのみ参照）。
- 冪等性：DB 保存は ON CONFLICT を用いて上書きし二重挿入を防止。
- フェイルセーフ：外部 API（OpenAI, J-Quants）失敗時はスキップやデフォルト値（例: macro_sentiment=0.0）で続行する設計が多く採用されています。
- セキュリティ：news_collector は SSRF 防止（プライベート IP 判定・リダイレクト検査）、defusedxml を使った XML パース、受信サイズ制限などを実装。

---

README の補足やサンプルスクリプト（cron/airflow 用のエントリポイント）などが必要であれば、目的（例: 日次 ETL を cron で回す、Slack 通知を組み込む、kabu ステーションと接続して発注する等）を教えてください。利用シナリオに合わせた具体的なサンプルやデプロイ手順、.env.example のテンプレートも作成できます。