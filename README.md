# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要 API の利用例）
- ディレクトリ構成
- 補足・設計方針

---

## プロジェクト概要
KabuSys は日本株の自動売買システム構築に必要なデータ取得・整備・解析機能を集約したライブラリです。J-Quants API からの株価・財務・カレンダー取得、RSS ベースのニュース収集、OpenAI を用いたニュースセンチメント評価、ETF を用いた市場レジーム判定、ファクター計算や品質チェック、監査ログ（トレーサビリティ）を DuckDB に永続化する機能を備えています。

---

## 機能一覧
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付整合性）
  - 日次 ETL の統合エントリポイント
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、gzip/サイズ上限、トラッキングパラメータ削除
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄単位のセンチメント集約（JSON Mode）
  - バッチ処理・リトライ・スコア検証・±1 でクリップ
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で daily レジーム判定
  - 冪等的に market_regime テーブルへ保存
- 研究用モジュール（research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、z-score 正規化
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - DB データがない場合は曜日ベースのフォールバック
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（DuckDB）
  - order_request_id による冪等制御、UTC タイムスタンプ保存

---

## 前提条件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ

（実際の requirements はプロジェクト配布時の packaging を参照してください）

---

## セットアップ手順

1. リポジトリを取得（例）
   git clone <repo-url>
2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate
3. パッケージをインストール
   pip install -e .   # または pip install duckdb openai defusedxml ...
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 下の「環境変数（.env）例」を参照
5. DuckDB 等の初期化（必要に応じて）
   - 監査ログ用 DB を作成する例（Python）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

注意:
- パッケージは src/ 配下にあるため setuptools の設定に合わせてインストールしてください（pip install -e . 推奨）。
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に自動で .env を読み込みます。テスト等で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（.env）例
必要なキー（最低限）:
- JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- SLACK_BOT_TOKEN=（Slack Bot Token）
- SLACK_CHANNEL_ID=（通知先チャンネルID）
- OPENAI_API_KEY=（OpenAI API キー）※score_news / score_regime 実行に必要
- KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
- LOG_LEVEL=INFO（または DEBUG/WARNING 等）
- DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
- SQLITE_PATH=data/monitoring.db（デフォルト）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## 使い方（主要 API の例）

- 日次 ETL を実行する（DuckDB 接続を渡す）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの NLP スコアを作成して ai_scores テーブルへ書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")

- 市場レジーム判定を実行する
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用

- 研究用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマの初期化（監査用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- マーケットカレンダーの更新ジョブ（夜間バッチ）
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)

注意:
- OpenAI 呼び出しは gpt-4o-mini（モデル名はモジュール内定義）を使用します。API 呼び出しはリトライとエラーハンドリングを備えていますが、API キーが必須です。
- score_news / score_regime はレスポンスパースの失敗や API 障害時にはフェイルセーフ（スコア 0.0 を使用・スキップ）する設計です。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / .env 自動読み込み・設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI 呼び出し・検証・保存）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS ニュース収集・正規化・保存
  - calendar_management.py — マーケットカレンダー管理・判定ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー / ランク
- ai, data, research 以下はさらに細かい実装コメントと設計方針がソース内に記載されています。

---

## 補足・設計方針（要点）
- Look-ahead バイアス対策:
  - 日時の自動参照（datetime.today() 等）をできるだけ抑え、target_date を引数で明示する設計。
  - データ取得時は fetched_at を UTC で記録。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を利用して冪等に。
  - 発注ログでは order_request_id を冪等キーとして扱う。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants / RSS 等）の障害やパース失敗時は、致命的エラーにせず可能な範囲で継続（ログ記録・スキップ・デフォルト値適用）。
- セキュリティ:
  - RSS 取得で SSRF 対策（プライベートIP 遮断、リダイレクト検査）、defusedxml を使用。
- テスト容易性:
  - OpenAI 呼び出し部分や URL open 部分はモック差し替えが想定されており、ユニットテストでの置換が可能。

---

何か追加したいサンプル（CLI スクリプトや docker-compose、requirements.txt など）や、特定モジュールの詳細な README セクションが必要であれば教えてください。