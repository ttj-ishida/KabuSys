# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・分析・監査・戦略実行に必要な機能群をモジュール化して提供するライブラリです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と LLM による銘柄別センチメントスコア化
- マクロ + テクニカル指標を用いた市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および研究ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注〜約定までの監査ログ（DuckDB ベース）の初期化と操作ユーティリティ
- 設定は環境変数 / .env による一元管理

設計の特徴として、ルックアヘッドバイアスを避ける実装（日時参照の管理）、API 呼び出しのリトライ/フェイルセーフ、DuckDB を用いたローカルデータ管理、および LLM（OpenAI）呼び出しの分離とフェイルセーフが挙げられます。

## 機能一覧

- config: 環境変数の読み込み・管理（.env 自動読み込み、必須キーの検証）
- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF/サイズ/追跡パラメータ対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal_events / order_requests / executions の DDL と初期化）
  - 統計ユーティリティ（Z スコア正規化 等）
- ai:
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを LLM（gpt-4o-mini）で評価し ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）200 日 MA とマクロニュース（LLM）を合成して market_regime に書き込み
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン計算、IC、統計サマリー など

## セットアップ手順

前提:
- Python 3.10+（typing の一部機能を使用）
- DuckDB をローカルで利用できること
- OpenAI API（LLM）を利用する場合は API キー
- J-Quants API 用のリフレッシュトークン

1. リポジトリをクローン／チェックアウトして、パッケージをインストール（開発モード推奨）:
   - 例:
     pip install -e .

2. 依存パッケージ（一例）:
   - duckdb
   - openai (openai SDK)
   - defusedxml
   - これらは pyproject.toml / requirements に従ってインストールしてください。

3. 環境変数の設定:
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 自動読み込みはデフォルト有効。テストや明示的制御が必要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

4. 必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb） デフォルトあり
   - SQLITE_PATH: 監視用 SQLite（デフォルトあり）
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

   （プロジェクトには .env.example を用意しておくことが推奨されます）

## 使い方（代表的な例）

以下は代表的な利用例です。実行は Python スクリプトやスケジューラ（cron / Airflow 等）から行います。

- DuckDB への接続（設定を利用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  # conn は上で生成済み
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアの算出（LLM 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY を環境に設定しておくか、第3引数に api_key を渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  res = score_regime(conn, target_date=date(2026,3,20))
  print("完了" if res == 1 else "失敗")

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # 以後 conn_audit で監査テーブルにアクセス

- ファクター計算 / 研究ユーティリティ
  from kabusys.research.factor_research import calc_momentum
  fm = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  norm = zscore_normalize(fm, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- LLM 呼び出し（score_news, score_regime）は OpenAI の利用料金が発生します。API キーの管理を行ってください。
- run_daily_etl 等は DB のスキーマ（raw_prices, raw_financials, market_calendar 等）が前提です。初期スキーマ生成はプロジェクトのスキーマ定義に従って行ってください（テーブルがない場合は ETL 内で処理が適切に行えない箇所があります）。

## よく使う設定と開発上のヒント

- 自動 .env ロードの無効化:
  - テスト時にプロセス外から環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- LOG_LEVEL/ KABUSYS_ENV による挙動差:
  - KABUSYS_ENV が `live` のときは実際の発注等のコードが有効化される想定（本リポジトリの発注モジュールは別途）。
- OpenAI 呼び出しのテスト置換:
  - モジュール内の `_call_openai_api` を unittest.mock.patch で差し替えることで外部 API を呼ばずにテストできます。
- DuckDB の executemany は空リストを受け付けないバージョンの注意:
  - 一部関数では executemany 前に空チェックが入っています（互換性確保のため）。

## ディレクトリ構成

概要（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの LLM センチメント化
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py            — RSS ニュース収集
    - calendar_management.py       — 市場カレンダー / 営業日ロジック
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログ（DDL / 初期化）
    - stats.py                     — 汎用統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — IC / 将来リターン / 統計サマリー
  - monitoring/ (※将来的な監視モジュール想定)
  - execution/  (※注文実行モジュール想定)
  - strategy/   (※戦略ロジック想定)

## ライセンス / 貢献

- ライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本コードベースには含まれていない場合があります）。

---

何か追加して欲しいセクション（例: CI 実行方法、詳細なスキーマ定義、.env.example の雛形 など）があれば教えてください。README に追記して整備します。