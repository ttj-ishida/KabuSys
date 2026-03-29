KabuSys — 日本株自動売買プラットフォーム (README)
======================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・AIによるニュースセンチメント評価・市場レジーム判定を含むデータプラットフォーム / 研究用ライブラリです。  
主に DuckDB をデータストアとして用い、J-Quants API からのデータ取得、RSS ベースのニュース収集、OpenAI（gpt-4o-mini）を用いたニュース NLP スコアリングやレジーム判定などを行います。  
本リポジトリはライブラリとして利用し、ETL バッチや研究解析、監査ログ初期化などをプログラム的に呼び出して利用します。

主な特徴
--------
- J-Quants API クライアント（株価・財務・マーケットカレンダー取得）  
  - レート制限（120 req/min）管理、再試行、401→トークンリフレッシュ処理を含む堅牢な実装
- ETL パイプライン（run_daily_etl、個別ETL）  
  - 差分取得・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
- AI モジュール（news_nlp / regime_detector）  
  - gpt-4o-mini の JSON-mode を用いた銘柄別ニュースセンチメント算出（ai_scores へ書き込み）  
  - ETF（1321）200日 MA とマクロニュースセンチメントを合成した市場レジーム判定
- 研究用モジュール（factor / feature exploration）  
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算、Z スコア正規化
- 監査ログ（audit）スキーマ初期化ユーティリティ（監査トレース用テーブル群）
- 設定管理（.env 自動読み込み、環境変数保護、必須設定チェック）

セットアップ手順
----------------

必要な前提
- Python 3.10+（タイプヒントで Union 演算子等を使用）
- DuckDB ライブラリ（duckdb）
- OpenAI の Python SDK（openai）
- defusedxml 等のユーティリティ

例: 仮想環境作成と依存インストール
- 仮想環境作成（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール（最低限）
  - pip install duckdb openai defusedxml

プロジェクトとしてローカルで開発・利用する場合（editable install）
- pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml がある階層）に .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。  
- 必須の環境変数（例）
  - JQUANTS_REFRESH_TOKEN=...      # J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD=...         # kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN=...           # Slack 通知に使用（必須）
  - SLACK_CHANNEL_ID=...          # Slack 送信先チャンネル（必須）
  - OPENAI_API_KEY=...            # OpenAI API キー（news_nlp / regime_detector 用）
- 任意 / デフォルトあり
  - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
  - LOG_LEVEL=INFO|DEBUG|...                     (デフォルト: INFO)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1              (自動 .env ロードを無効にする)
  - DUCKDB_PATH=data/kabusys.duckdb               (デフォルトパス)
  - SQLITE_PATH=data/monitoring.db

例 (.env)
  JQUANTS_REFRESH_TOKEN=eyJ...your-refresh-token...
  OPENAI_API_KEY=sk-...
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C12345678
  KABU_API_PASSWORD=yourpassword
  KABUSYS_ENV=development
  LOG_LEVEL=DEBUG

注意:
- Settings クラスは環境変数を読み取り、必須変数が未設定の場合は ValueError を投げます。

使い方（簡単な API 呼び出し例）
------------------------------

1) DuckDB 接続の準備（デフォルトは settings.duckdb_path）
- Python から利用する例:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))

2) 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が対象（内部で営業日に調整される）
  result = run_daily_etl(conn, target_date=None)
  print(result.to_dict())

3) ニュースセンチメント算出（AI）
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # DuckDB 接続を用意して target_date を指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込み銘柄数: {written}")

  - score_news は OPENAI_API_KEY の環境変数または api_key 引数を参照します。
  - 失敗してもフェイルセーフで進む設計（失敗した銘柄はスキップされる）。

4) 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルへ書き込みが行われる

5) 監査ログ用 DuckDB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 必要なテーブル・インデックスが作成されます

6) 研究モジュールの利用例
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))

各モジュールの説明（要点）
-----------------------
- kabusys.config
  - .env 自動読み込み機能（.env / .env.local）および Settings による環境変数アクセス
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ロジック）
  - pipeline / etl: ETL 実行（run_daily_etl など）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査テーブル定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp: 銘柄別ニュースセンチメントを OpenAI で算出し ai_scores に格納
  - regime_detector: ETF MA とマクロニュースによる市場レジーム判定
- kabusys.research
  - factor_research: Momentum, Value, Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算・IC・統計サマリー・ランキング

ディレクトリ構成
-----------------
src/
  kabusys/
    __init__.py                -- パッケージ初期化、バージョン定義
    config.py                  -- 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py              -- ニュース NLP スコアリング
      regime_detector.py       -- 市場レジーム判定
    data/
      __init__.py
      jquants_client.py        -- J-Quants API クライアント + DuckDB 保存
      pipeline.py              -- ETL パイプライン（run_daily_etl など）
      etl.py                   -- ETLResult の再エクスポート
      news_collector.py        -- RSS 収集・前処理
      calendar_management.py   -- マーケットカレンダー管理/営業日判定
      quality.py               -- データ品質チェック
      audit.py                 -- 監査ログスキーマ初期化
      stats.py                 -- 統計ユーティリティ
    research/
      __init__.py
      factor_research.py       -- ファクター計算
      feature_exploration.py   -- 将来リターン / IC / サマリー
    research/ ... (その他モジュール)
  (プロジェクトルートに pyproject.toml 等がある想定)

運用上の注意点
-------------
- Look-ahead バイアス対策が設計に組み込まれています（target_date ベースの処理で datetime.today() を無闇に参照しない等）。
- OpenAI API 呼び出しは外部サービス依存のため、レスポンスエラー時は安全側（0.0 スコア等）で継続する設計です。ただし API キー等は適切に管理してください。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあります。本コードはその制約に配慮していますが、DuckDB のバージョン差異に注意してください。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。CI/テスト環境에서는 KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能です。

サンプル / デバッグのヒント
--------------------------
- ログレベルは LOG_LEVEL で制御（DEBUG/INFO 等）。開発時は LOG_LEVEL=DEBUG を設定してください。
- OpenAI 呼び出しをユニットテストで差し替える場合、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックすると容易です。
- RSS 取得や外部 API 呼び出しはネットワーク依存のため、テスト時はネットワークコールをモックすることを推奨します。

ライセンス / 貢献
-----------------
（ここに適切なライセンス情報や貢献ガイドラインを追記してください）

補足
----
この README はリポジトリ内のコードを基に作成しています。実際に運用するには pyproject.toml / requirements.txt を整備し、CI やシークレット管理（Vault 等）を導入することを推奨します。必要であればインストール要件、サンプル .env.example、運用 runbook（クラウド上のバッチ実行や Slack 通知の設定）などのテンプレートも作成します。必要な場合は教えてください。