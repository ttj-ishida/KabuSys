# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群。J-Quants / RSS / OpenAI 等の外部データを取り込み、データETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログ等を提供します。

---

## プロジェクト概要

KabuSys は日本株の量的取引（リサーチ → シグナル生成 → 発注）を支えるライブラリ群です。主に以下を目的としています。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と LLM（OpenAI）によるニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF の移動平均乖離とマクロニュースの LLM センチメントを合成）
- ファクター計算・特徴量探索・統計ユーティリティ（研究用）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の特徴として、バックテストでのルックアヘッドバイアスを防ぐために「実行時の現在時刻を直接参照しない」「DBクエリで date < target_date など排他条件を用いる」方針が貫かれています。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
- データ品質
  - 欠損 / スパイク / 重複 / 日付整合性チェック（kabusys.data.quality）
- ニュース収集・前処理
  - RSS フィード取得・正規化・SSRF対策・トラッキングパラメータ削除（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - 銘柄単位スコアリング（kabusys.ai.news_nlp）
  - マクロニュースを用いた市場レジーム判定（kabusys.ai.regime_detector）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ（kabusys.research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - 監査テーブル定義・初期化ユーティリティ（kabusys.data.audit）
- 環境設定
  - .env 自動読み込み / 環境変数アクセスをラップ（kabusys.config）

---

## セットアップ手順

前提：
- Python 3.10+ を推奨（型注釈で | を使用）
- DuckDB, OpenAI SDK, defusedxml 等がインストールされていること

1. リポジトリをクローン（またはパッケージを配置）
   - 例: git clone ...

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - 開発環境で editable にインストール:
     - pip install -e .
   - 必要な依存（代表例）:
     - pip install duckdb openai defusedxml

   （プロジェクトの pyproject.toml / requirements を参照して依存を整えてください）

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を配置できます。
   - 自動ロードの順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（少なくとも以下は設定が必要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD    : kabuステーション API パスワード（発注を行う場合）
   - SLACK_BOT_TOKEN      : Slack 通知を使う場合
   - SLACK_CHANNEL_ID     : Slack チャンネル ID
   - OPENAI_API_KEY       : OpenAI の API キー（score_news / score_regime を使う場合）

   その他:
   - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視DB 用、デフォルト data/monitoring.db）

5. DB 初期化（監査ログ等）
   - 例: Python スクリプト内で
     - import duckdb
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主なユースケース例）

以下は簡単な Python スニペット例です。実運用ではログ設定・エラーハンドリング等を適切に行ってください。

- DuckDB に接続して日次 ETL を実行する
  - 目的: J-Quants から差分取得して raw_prices / raw_financials / market_calendar を更新し品質チェック
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn)  # target_date 省略で今日が対象
      print(result.to_dict())

- ニュースセンチメント（銘柄単位）を生成する
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
      print(f"written: {written}")

- 市場レジーム判定を実行する
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      from kabusys.config import settings

      conn = duckdb.connect(str(settings.duckdb_path))
      score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマを初期化する（既存 DuckDB 接続へテーブル追加）
  - 例:
    - import duckdb
      from kabusys.data.audit import init_audit_schema
      conn = duckdb.connect("data/kabusys.duckdb")
      init_audit_schema(conn, transactional=True)

- J-Quants から単独で上場銘柄情報を取得する
  - 例:
    - from kabusys.data.jquants_client import fetch_listed_info
      infos = fetch_listed_info(date_=date(2026,3,1))
      print(len(infos))

注意点:
- OpenAI 呼び出しはコストとレート制限に注意してください。score_news と score_regime は内部でリトライ・バッチ処理を行いますが、API キーの用意と利用量の管理が必要です。
- run_daily_etl 等は DB 上のテーブルスキーマ（raw_prices / raw_financials / market_calendar / ai_scores 等）が前提です。初期スキーマは別途準備してください（本コードベースにはスキーマ初期化の全面実装は含まれていない箇所があります）。

---

## 環境変数・設定（要点）

- 自動 .env ロード
  - パッケージ読み込み時にプロジェクトルートを探索して `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
  - .env のパースはシェルライク（export KEY=val / コメント / クォート対応）。

- Settings API
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path などでアクセス可能。

- KABUSYS_ENV の有効値:
  - development, paper_trading, live

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings 定義
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM スコアリング（銘柄別）
  - regime_detector.py  — ETF MA とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - etl.py                — ETL 結果クラス再エクスポート
  - pipeline.py           — 日次 ETL パイプライン実装（run_daily_etl 等）
  - stats.py              — z-score 正規化 等の統計ユーティリティ
  - quality.py            — データ品質チェック（欠損・重複・スパイク等）
  - audit.py              — 監査ログ（シグナル/発注/約定）スキーマ作成
  - jquants_client.py     — J-Quants API クライアント（取得・保存関数）
  - news_collector.py     — RSS 取得・前処理・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py        — momentum / value / volatility 計算
  - feature_exploration.py    — 将来リターン, IC, factor_summary, rank
- research/*, ai/* などは研究・解析向けの関数群

（上記ファイル毎に docstring で設計方針・入出力・注意点が詳細に書かれています。利用時は該当モジュールの docstring を参照してください。）

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアス防止
  - 多くの関数（score_news / score_regime / ETL）は内部で date の比較を厳密に行い、実行時の現在時刻を直接参照しない実装になっています。バックテストでの使用時は target_date を明示的に与えてください。
- API レート／コスト管理
  - J-Quants はリクエストレート制御（デフォルト 120 req/min）を実装しています。OpenAI 呼び出しもバッチ・リトライを行いますが、利用量には注意してください。
- DB スキーマ
  - DuckDB のテーブルスキーマやインデックスはコードの期待と一致させる必要があります。監査ログ用スキーマは kabusys.data.audit の init 関数で初期化可能です。
- テストと環境分離
  - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使うことでユニットテストでの環境制御が容易になります。

---

README に書ききれない詳細は各モジュールの docstring（src/kabusys 以下）を参照してください。使い方に関する個別の例やスクリプトが必要であれば、目的（ETL 実行 / ニューススコアリング / レジーム判定 等）を教えてください。サンプルスクリプトを用意します。