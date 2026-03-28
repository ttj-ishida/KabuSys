# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
株価・財務・カレンダーのETL、ニュース収集・NLPによる銘柄センチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ用スキーマ等のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の機能群を備えた内部向けライブラリです。

- J-Quants API を用いたデータ取得（株価日足 / 財務 / カレンダー / 上場銘柄一覧）
- DuckDB をデータレイクとして用いる差分ETLパイプライン（冪等保存・品質チェック付き）
- RSS ニュース収集と前処理（SSRF対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini など）でのニュースセンチメント解析（銘柄単位・バッチ処理）
- マーケットレジーム判定（ETF の MA 乖離とマクロニュースの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- 取引監査ログスキーマ（シグナル → 発注 → 約定 のトレーサビリティ）

設計方針として、バックテストのルックアヘッドバイアスを避ける実装、外部API呼び出しのリトライ・フェイルセーフ、DuckDB 側での冪等保存・トランザクション管理を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集（RSS の取得・前処理・保存）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（init_audit_db / init_audit_schema）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロニュースで日次の市場レジーム判定
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数・設定管理（.env 自動ロード、settings オブジェクト）

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone <your-repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール  
   ※プロジェクトに requirements.txt が無い場合は仮想環境に以下を手動で入れてください（最低限）:
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリ以外のパッケージが必要な場合があります。

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / setup.py があれば pip install -e . を使用）

4. 環境変数の設定  
   ルートに `.env` を置くと自動で読み込まれます（CWD に依存せずパッケージ位置からプロジェクトルートを探索）。テストなどで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（運用時）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（通知等で使用する場合）
   - SLACK_CHANNEL_ID      : Slack チャンネルID

   任意 / デフォルトあり:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で .env 自動ロードを無効化
   - DUCKDB_PATH （デフォルト data/kabusys.duckdb）
   - SQLITE_PATH （デフォルト data/monitoring.db）
   - KABU_API_BASE_URL （デフォルト http://localhost:18080/kabusapi）
   - OPENAI_API_KEY はスクリプト呼び出し時に引数で渡すことも可能（score_news/score_regime など）。省略時は環境変数を参照します。

   .env のサンプル（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - OPENAI_API_KEY=sk-xxxxx
   - KABU_API_PASSWORD=your_password
   - SLACK_BOT_TOKEN=xoxb-xxxxx
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB データベース用ディレクトリ作成（パスは settings.duckdb_path に基づく）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL / スクリプト内での利用例です。ここでは duckdb を直接接続し、公開 API を呼ぶ例を示します。

- ETL（日次）を実行する
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))  # または duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に保存（OpenAI API キーは環境変数か引数で指定）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  - print(f"書き込み件数: {written}")

- マーケットレジーム判定を実行（ETF 1321 の MA とマクロニュースで判定）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ用 DuckDB を初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- 設定値へアクセス
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env, settings.is_live)

注意:
- score_news / score_regime などの OpenAI 呼び出しはレイテンシ・料金が発生します。テスト時はモック可能です（各モジュール内 _call_openai_api をパッチ）。
- run_daily_etl は内部で calendar ETL → prices ETL → financials ETL → 品質チェック の順で実行します。個別に実行することも可能です。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ初期化、version 情報
- config.py — 環境変数・設定管理（.env 自動ロード、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのバッチセンチメント解析と ai_scores への書込
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save/認証/リトライ/レートリミット）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETL インターフェース（ETLResult の再エクスポート）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS フィードの収集・前処理
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログ（DDL／スキーマ初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（mom/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

その他:
- ドキュメント（Design/MD ファイル）や CI 設定があればプロジェクトルートに配置されます。

---

## 実運用上の注意とヒント

- 環境管理
  - .env はプロジェクトルートに置くと自動読み込みされます（ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 機密情報（トークン等）は安全な方法で管理してください（Secrets Manager 等）。

- OpenAI 呼び出し
  - API のレートや料金に注意してください。score_news は銘柄をバッチ（最大 20 銘柄 / call）で処理します。
  - テスト時は _call_openai_api をモックすることを推奨します。

- J-Quants API
  - rate limit（120 req/min）をモジュール内で制御しています。ID トークンはリフレッシュ処理が組み込まれています。

- DuckDB
  - テーブルスキーマや初期化はプロジェクト内のスクリプト／DDL に従ってください（audit.init_audit_db などのユーティリティあり）。

---

ご不明点・追加してほしい章（例: API リファレンス、スキーマ定義、運用手順）などがあればお知らせください。README の内容を用途に応じて拡張します。