KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
---
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP、マーケットレジーム判定、監査ログなどを含む汎用ライブラリ群です。本リポジトリは主に以下の責務を持ちます。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いた ETL / 永続化（raw_prices、raw_financials、market_calendar 等）
- ニュース収集と LLM による銘柄毎センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算・IC/統計ユーティリティ
- 発注/約定の監査ログテーブル初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

主な機能一覧
---
- データ取得・保存
  - J-Quants クライアント：fetch / save（株価日足・財務・カレンダー・上場銘柄情報）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース処理・AI
  - RSS 取得・前処理（news_collector）
  - 銘柄別ニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - マクロニュースと ETF MA に基づく市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合の検出（kabusys.data.quality.run_all_checks）
- 監査（Audit / Traceability）
  - signal_events / order_requests / executions 等のテーブル DDL と初期化関数（kabusys.data.audit）

セットアップ手順
---
前提
- Python 3.10 以上（typing の | 型等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1) 仮想環境を作成・有効化（推奨）
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1

2) 依存パッケージをインストール
- 代表的な依存:
  - duckdb, openai, defusedxml
- 例:
  - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3) ソースをインストール（開発モード）
- repository のルートで:
  - pip install -e .

4) 環境変数 / .env の準備
- プロジェクトルートに .env または .env.local を置くと自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 必要な主要環境変数（例）:
  - JQUANTS_REFRESH_TOKEN=（必須：J-Quants の refresh token）
  - KABU_API_PASSWORD=（必須: kabuステーション API パスワード）
  - OPENAI_API_KEY=（AI 機能を使う場合に必要）
  - KABU_API_BASE_URL=（省略可、デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH=data/monitoring.db（監視用 SQLite）
  - LOG_LEVEL=INFO（デフォルト）
- 簡易 .env 例:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=sk-...
  - KABU_API_PASSWORD=your_kabu_password
  - DUCKDB_PATH=data/kabusys.duckdb
  - LOG_LEVEL=DEBUG

使い方（基本例）
---

共通準備
- DuckDB 接続:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

ETL（1日分のデータ更新）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(res.to_dict())

個別 ETL
- run_prices_etl / run_financials_etl / run_calendar_etl を利用可能。

ニューススコア取得（LLM 必須）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照

市場レジーム判定（LLM 必須）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- momentum = calc_momentum(conn, target_date=date(2026,3,20))

データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

監査テーブル初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

設定周りの注意
- 自動 .env ロード: kabusys.config モジュールがプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が足りない場合、settings の該当プロパティが ValueError を投げます。

主なモジュール / ディレクトリ構成
---
（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と .env の読み込み・Settings クラス定義
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースセンチメント算出。OpenAI（gpt-4o-mini）を使用するプロンプト・バリデーション・リトライを備える。
    - regime_detector.py
      - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成し market_regime テーブルへ保存。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、認証リフレッシュ、レートリミット、リトライ）
    - pipeline.py
      - 日次 ETL パイプライン（差分取得・保存・品質チェック）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得、正規化、SSRF 対策、raw_news への保存ロジック
    - calendar_management.py
      - market_calendar の更新と営業日判定ユーティリティ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査テーブル（signal_events / order_requests / executions）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

運用上の留意点 / ベストプラクティス
---
- Look-ahead バイアス対策が設計に組み込まれています：関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し元が target_date を明示することを期待します。バックテストや再現性のために target_date を明示してください。
- OpenAI や J-Quants の API 呼び出しはレート制限・リトライ処理を行いますが、API キーの有効期限やコストには注意してください。
- DuckDB への書き込みは冪等的（ON CONFLICT DO UPDATE / DO NOTHING）を目指していますが、ETL の途中失敗時に一部データが反映される可能性があります。必要に応じてトランザクション管理を検討してください。
- news_collector は SSRF 対策や受信サイズ制限を備えていますが、RSS ソースの追加時は信頼性・ライセンスに注意してください。

トラブルシューティング（簡易）
---
- 環境変数が読み込まれない:
  - プロジェクトルートに .env があるか、KABUSYS_DISABLE_AUTO_ENV_LOAD が 0 になっているか確認。強制的に無効化されている場合は解除するか、環境に直接 export してください。
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY を正しく設定しているか、API の利用制限（モデル可否）を確認してください。score_news/score_regime は API 失敗時にフェールセーフでスコア 0 を使う場合がありますが、API キー未設定だと ValueError を投げます。
- J-Quants API 関連:
  - JQUANTS_REFRESH_TOKEN を設定してください。get_id_token が自動で refresh を行います。
  - API レスポンスや認証エラーはログに詳細が出ます。

ライセンス・貢献
---
- 本 README ではライセンスファイルの記載はしていません。実プロジェクトで配布する場合は LICENSE ファイルを追加してください。
- バグ修正や機能追加は Pull Request を歓迎します。変更前に issue をあげて設計方針を相談してください。

最後に
---
この README はコードベースの主要な使い方と構成をまとめたものです。個別の関数や API の詳細挙動は各モジュールの docstring を参照してください（kabusys/* 内）。必要ならばサンプルスクリプトやデプロイ手順（systemd / supervisor / コンテナ化）等の運用ドキュメントも別途作成できます。要望があれば作成します。