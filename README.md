# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants） → ETL → 品質チェック → ファクター計算 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログ（発注〜約定のトレース）までを一貫して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下の要件を満たすことを目的に設計された Python ライブラリです。

- J-Quants API からの株価/財務/カレンダー取得（レート制御・リトライ付き）
- DuckDB を用いたローカルデータプラットフォームと冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 研究用途のファクター計算・特徴量解析（バックテスト用のユーティリティ）
- ニュース収集・前処理・LLM によるニュースセンチメント（gpt-4o-mini を想定）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 監査ログスキーマ（signal → order_request → execution の追跡）

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「フォールバックによる堅牢性」「外部依存最小化（標準ライブラリ優先）」を重視しています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch / save / pagination / token refresh）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - マーケットカレンダー管理・営業日判定（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS パーシング、URL 正規化、SSRF 対策）
  - 監査ログ（テーブル定義・初期化 helper: init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
- ai
  - ニュース NLP（銘柄別センチメントを OpenAI に渡して取得）
  - 市場レジーム判定（ETF MA200 乖離 + マクロセンチメントの合成）
- config
  - 環境変数 / .env 自動ロード（プロジェクトルート検出、.env / .env.local 読み込み）
  - settings オブジェクト経由で設定アクセス

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing の演算子などを使用）
- DuckDB を利用するため `duckdb` パッケージが必要
- OpenAI を使う場合は `openai` SDK が必要
- ニュース収集に `defusedxml` を使用

1. リポジトリをクローン（例）
   git clone <repo-url>
2. 開発環境へインストール（プロジェクトルートに `pyproject.toml` がある想定）
   - 仮想環境を作る（推奨）
     python -m venv .venv
     source .venv/bin/activate
   - インストール（例: pip）
     pip install -e .[all]
   ※ 実パッケージ名や extras は環境に応じて調整してください。
3. 必要な環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` を作成することで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL に必要）
     - KABU_API_PASSWORD: kabuステーション API を使う場合に必要
     - KABU_API_BASE_URL: kabu API の base url（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に必要
     - OPENAI_API_KEY: OpenAI を使う AI 機能に必要（score_news / score_regime）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など運用設定
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...
4. データベース初期化（監査ログ schema を準備）
   Python から:
   from pathlib import Path
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(Path(settings.duckdb_path))
   # conn をそのまま使えます
   または既存 DuckDB 接続に schema を追加する:
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect(str(settings.duckdb_path))
   init_audit_schema(conn, transactional=True)

---

## 使い方（簡単なコード例）

以下は主要機能をプログラムから呼び出すためのサンプルです。

- DuckDB 接続の作成
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（株価 / 財務 / カレンダー の差分取得と品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを生成（OpenAI API を使用）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OPENAI_API_KEY が環境変数に入っているか、api_key 引数を渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"スコアを書き込んだ銘柄数: {written}")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  moments = calc_momentum(conn, date(2026,3,20))
  values = calc_value(conn, date(2026,3,20))

- 統計正規化ユーティリティ
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(moments, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- OpenAI を利用する関数は API の呼び出しやレスポンスパースにフォールバックロジックを備えていますが、APIキーの設定は必須です。
- J-Quants へのリクエストは rate limit（120 req/min）を遵守する内部実装です。ID トークンが必要で、settings.jquants_refresh_token を .env に設定してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須 for ETL)
- OPENAI_API_KEY (必須 for AI 機能 or pass via api_key)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト用）

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## ディレクトリ構成

（主要ファイル・モジュールの一覧）

src/kabusys/
- __init__.py
- config.py                       : 環境変数 / .env ローディングと Settings
- ai/
  - __init__.py
  - news_nlp.py                    : ニュースセンチメント（銘柄別）取得ロジック
  - regime_detector.py             : ETF MA + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              : J-Quants API クライアント（fetch/save, pagination, token）
  - pipeline.py                    : ETL パイプライン（run_daily_etl 他）
  - etl.py                         : ETLResult の再エクスポート
  - quality.py                     : データ品質チェック
  - stats.py                       : zscore_normalize 等の統計ユーティリティ
  - calendar_management.py         : マーケットカレンダー・営業日ロジック
  - news_collector.py              : RSS 収集・前処理・SSRF 対策
  - audit.py                       : 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py             : ファクター計算（momentum/value/volatility）
  - feature_exploration.py         : 将来リターン計算、IC、統計サマリー
- monitoring/ (存在する場合: 監視関連モジュール) ※今回コードベースには監視モジュール参照あり
- execution/   (注文実行関連: 外部 API 連携層) ※実装に依存

テスト用 / ドキュメント用補助ファイルはリポジトリに応じて配置してください。

---

## 運用上の注意

- Look-ahead バイアス防止: 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストでは必ず適切な過去日を渡してください。
- 冪等性: J-Quants 保存関数は ON CONFLICT DO UPDATE を使って冪等に保存します。
- エラーハンドリング: AI / API 呼び出しはフェイルセーフ（一定のフォールバック値を使用）で動作しますが、重要な運用時にはログ監視とアラート設定を推奨します。
- セキュリティ: news_collector は SSRF 対策・XML パース保護（defusedxml）・受信サイズ制限を実装しています。外部 URL の取り扱いには引き続き注意してください。

---

もし README に追加したい具体的な使用例（CLI スクリプト、Dockerfile、CI ワークフロー、.env.example など）があれば、その内容に沿って拡張版を作成します。