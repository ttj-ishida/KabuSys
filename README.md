KabuSys
=======

プロジェクト概要
---------------
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースセンチメント分析・市場レジーム判定・監査ログ基盤を備えた自動売買／リサーチ向けライブラリです。J-Quants・RSS・OpenAI（LLM）など外部データソースを統合し、DuckDB を中心にデータを保管・処理します。設計上、バックテストにおけるルックアヘッドバイアス回避やフェイルセーフ性（API失敗時のフォールバック）を重視しています。

主な機能一覧
-------------
- データ収集（J-Quants）
  - 株価日足（OHLCV）の差分取得・保存（fetch / save）
  - 財務データ（四半期 BS/PL）取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 差分更新・バックフィル・ページネーション・トークン自動更新対応
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- ニュース収集／前処理
  - RSS フィード収集（SSRF 対策・応答サイズ制限・URL 正規化）
  - raw_news / news_symbols への冪等保存処理
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメント付与（score_news）
  - マクロニュースから市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、リトライやバリデーション付き
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターンの計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査（Audit）テーブル
  - signal_events / order_requests / executions を含む監査スキーマの作成と初期化
  - 監査 DB を冪等的に作成するユーティリティ（init_audit_db / init_audit_schema）

動作要件（主な依存）
-------------------
- Python >= 3.10
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- 標準ライブラリ（urllib, json, logging 等）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... （本ドキュメントではリポジトリ URL を省略）

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージ化されている場合）pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD に依存せず、パッケージ導入後も機能）。
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の例（必要なキー）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=your_openai_api_key
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

主な使い方（コード例）
---------------------

※ 以下はライブラリをインポートして直接呼び出す最小例です。接続先 DB や API キーは環境変数や引数で渡してください。

- DuckDB 接続の作成（設定からパスを利用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # デフォルトで今日を対象
  print(result.to_dict())

- ニュースセンチメントのスコア付与
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  ret = score_regime(conn, target_date=date(2026, 3, 20))
  print("regime scored:", ret)

- 監査 DB 初期化（監査専用 DB 作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は初期化済みの DuckDB 接続

- 設定（Settings）の利用
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

設計上の注意点 / 挙動メモ
-------------------------
- Look-ahead バイアス対策
  - 多くの処理（news window, MA/forward returns など）は target_date より未来のデータを参照しないよう設計されています（date の比較で厳密に排除）。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants 等）に失敗した場合、多くの箇所でデフォルト値（例: macro_sentiment=0.0）にフォールバックし処理を継続します。重大な DB 書き込み失敗等は例外を投げ上位に伝播します。
- 自動 .env ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを抑止できます。
- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI を JSON Mode（response_format={"type":"json_object"}）で呼び出します。API 失敗はリトライ／バリデーション後に安全に扱われます。
- DuckDB バインド
  - DuckDB の executemany に空パラメータを渡すとバージョンによってエラーになるため、空チェックを行い処理する設計です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリ内の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（score_news）
    - regime_detector.py     # マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py# マーケットカレンダー管理
    - news_collector.py     # RSS ニュース収集
    - quality.py            # データ品質チェック
    - stats.py              # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py              # 監査ログ（監査スキーマ初期化）
    - etl.py (exports ETLResult)
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/value/volatility）
    - feature_exploration.py# 将来リターン / IC / 統計サマリー

よくある運用フロー（例）
-----------------------
- 夜間バッチ（Crontab 等）
  1. DuckDB に接続
  2. run_daily_etl(conn) を実行（データ取得・保存・品質チェック）
  3. score_news(conn, target_date) を実行して ai_scores を更新
  4. score_regime(conn, target_date) を実行して market_regime を更新
  5. 結果を Slack 等に通知（Slack トークンは settings 参照）

トラブルシューティング
-----------------------
- 環境変数が見つからない
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は未設定時に ValueError を投げます。.env を用意するか環境変数を直接設定してください。
- OpenAI 呼び出しでエラーが出る
  - OPENAI_API_KEY を設定してください。API レートや 5xx/429 を考慮して内部でリトライ処理が行われますが、一定回数でフォールバック（スコア 0）する設計です。
- DuckDB に関するエラー
  - executemany に空リストを渡す場面があるため、ライブラリは空チェックをしています。DuckDB のバージョン差に注意してください（推奨は最新の安定版）。

貢献 / ライセンス
-----------------
（この README では記載していません。実運用リポジトリであれば CONTRIBUTING / LICENSE を追加してください。）

以上。必要であれば、README にサンプル .env.example、CI 実行手順、ユニットテスト／モック方針などの追記も可能です。どの情報を追加しますか？