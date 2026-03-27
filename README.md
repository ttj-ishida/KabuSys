# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB を中心としたデータ ETL、ニュース NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などのユーティリティを提供します。

主な目的は「バックテスト・リサーチ環境と運用環境で共通に使える、安全で冪等なデータ処理 / スコアリング基盤」を提供することです。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（必要に応じて無効化可能）
  - 必須設定の取得ラッパー（未設定時は例外）
- データ ETL（J-Quants API 連携）
  - 株価日足（OHLCV）取得・保存（ページネーション、レート制限、トークン自動リフレッシュ、冪等保存）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（run_daily_etl）と個別ジョブ（prices/financials/calendar）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 対応、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント評価（gpt-4o-mini, JSON Mode） → ai_scores へ書き込み
  - 1チャンク最大 20 銘柄、リトライ/バックオフ、レスポンスバリデーション
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成
  - market_regime テーブルへの冪等書き込み
  - API失敗や不足データ時のフェイルセーフ設計
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルなどを初期化する DDL / インデックス
  - init_audit_db により専用 DuckDB を初期化して返す

---

## セットアップ手順

前提:
- Python 3.9+
- DuckDB を動かせる環境
- OpenAI API キー（LLM を使う場合）
- J-Quants のリフレッシュトークン（データ ETL を行う場合）
- 必要パッケージ（下記参照）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージ（代表的なもの）
   - duckdb
   - openai (OpenAI の Python SDK)
   - defusedxml
   - requests（プロジェクトにより不要な場合あり）
   - 例:
     - pip install duckdb openai defusedxml

   （実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml や setup.py がある想定）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。
   - 主に必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_station_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   サンプル (.env.example) をプロジェクトに置いておくことを推奨します。

注意:
- 自動ロードはパッケージ内の config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して .env を読み込みます。テスト時などで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要な例）

以下では簡単な Python スニペットでの利用例を示します。事前に必要な環境変数を設定し、duckdb パッケージがインストールされている前提です。

- DuckDB 接続と日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(<path/to/duckdb>))  # 例: str(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄ごと）をスコアリングして ai_scores に保存
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込み

- 監査ログ用 DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査ログへ書き込み・参照が可能

- 研究用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))

注意点:
- LLM 呼び出し（score_news / score_regime）では OpenAI API キーが必要です。api_key 引数で明示的に与えるか、環境変数 OPENAI_API_KEY を設定してください。未設定だと ValueError が発生します。
- ETL・API 呼び出しはネットワークや外部サービスに依存するため、リトライ・フェイルセーフが組み込まれています。ログを確認して問題を対応してください。

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
- OPENAI_API_KEY: OpenAI API キー（必須：LLM を使う機能）
- KABU_API_PASSWORD: kabu ステーション API パスワード（自動売買周り）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると自動で .env を読み込まない

設定値は kabusys.config.settings からプロパティとしてアクセスできます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要ファイルとモジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込み、設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（銘柄別）処理
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py            — RSS ニュース収集（SSRF 対策など）
    - calendar_management.py       — 市場カレンダー、営業日ロジック
    - quality.py                   — データ品質チェック
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログテーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー

その他:
- setup 配置や pyproject.toml（プロジェクトルート）に依存してパッケージ化・インストールを行います。

---

## 運用上の注意・設計上のポイント

- Look-ahead バイアス防止:
  - バックテスト・ファクター計算で datetime.today() を直接参照しない実装方針。
  - ETL/研究関数は target_date を明示的に受け取り、その日以前のデータのみを参照するよう設計されています。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT により冪等に実行されることを想定。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）でエラーが発生しても、システム全体が停止しないように設計され、必要に応じてデフォルト値やログで継続します。
- セキュリティ:
  - RSS 取り込み時の SSRF 対策、defusedxml による XML パース安全化、プライベートアドレスの排除等を実装。
  - OpenAI / J-Quants トークンは環境変数で管理し、ソースコードやコミットに含めないこと。

---

必要に応じて README を拡張して、CI / デプロイ手順、実際のテーブルスキーマ（DDL）やサンプル .env.example を追記してください。README の補足や特定機能（例: ETL の scheduler 連携例や Slack 通知連携例）を追記したい場合は要望を教えてください。