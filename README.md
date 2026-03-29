# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（モジュール群）。  
DuckDB をデータレイヤに用い、J-Quants / RSS / OpenAI（LLM）などを組み合わせて、データ取得（ETL）・品質チェック・ニュースNLPによる銘柄スコアリング・市場レジーム判定・監査ログ管理を提供します。

---

## 主要機能

- データ取得（J-Quants）・ETL パイプライン
  - 日次 ETL（株価・財務・カレンダーの差分取得 + 品質チェック）
  - 差分取得・バックフィル・ページネーション・リトライ・レート制御を実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（JPX カレンダーの取得・営業日判定）
- ニュース収集（RSS）とニュース前処理（SSRF 保護・トラッキング除去）
- ニュースの LLM ベースセンチメント解析（gpt-4o-mini を想定）
  - 銘柄単位にまとめてバッチでスコアを取得、ai_scores に書き込み
- 市場レジーム判定
  - ETF（1321）の 200 日 MA とマクロニュースの LLM センチメントを合成
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- 監査ログ（signal → order_request → execution）テーブル定義・初期化ユーティリティ

---

## 動作要件

- Python 3.10 以上（型ヒントに `X | None` 構文を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS フィードへの HTTP(S)

（実際の環境では追加の依存関係やバージョン固定が必要になる場合があります。requirements.txt を用意してください）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンし仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. プロジェクトルートに .env を用意（自動で読み込まれます）
   - 自動読み込みは `kabusys.config` がプロジェクトルート（.git または pyproject.toml）を検出した場合に行います。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

---

## 環境変数（.env の例）

以下は主要な環境変数（.env に設定する想定）:

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (デフォルト)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb   (デフォルト)
- SQLITE_PATH=data/monitoring.db    (デフォルト)
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY=...  （news_nlp / regime_detector 用。関数呼び出し時に api_key を渡すことも可）

注意: 必須の値を取得するプロパティは `kabusys.config.settings` でチェックされ、未設定時は ValueError になります。

---

## 使い方（主要な例）

※ ここでは Python インタープリタ／スクリプトからの利用例を示します。各関数は duckdb.DuckDBPyConnection を受け取ります。

1. DuckDB 接続を作る（ファイルベース）
   - import duckdb
   - from kabusys.config import settings
   - conn = duckdb.connect(str(settings.duckdb_path))

2. 日次 ETL を実行する
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - print(result.to_dict())

3. ニュース NLP（銘柄別スコア）を実行する
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - written = score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
   - print(f"written: {written} codes")

4. 市場レジーム判定を実行する
   - from kabusys.ai.regime_detector import score_regime
   - from datetime import date
   - status = score_regime(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))

5. マーケットカレンダー更新ジョブ実行
   - from kabusys.data.calendar_management import calendar_update_job
   - saved = calendar_update_job(conn)
   - print("saved", saved)

6. 監査ログ用 DB 初期化
   - from kabusys.data.audit import init_audit_db, init_audit_schema
   - audit_conn = init_audit_db("data/audit.duckdb")  # ファイルを作ってスキーマを初期化
   - あるいは既存 conn にテーブルを追加:
     - init_audit_schema(conn, transactional=True)

7. 研究用ファクター計算例
   - from kabusys.research.factor_research import calc_momentum
   - records = calc_momentum(conn, target_date=date(2026,3,20))

---

## 注意点・設計方針（抜粋）

- ルックアヘッドバイアス回避:
  - 各モジュールは内部で datetime.today() / date.today() を直接参照しないよう配慮（関数は target_date を引数に取る）。
- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE などで冪等性を確保。
  - audit の order_request_id / broker_execution_id は冪等キーとして扱う。
- フェイルセーフ:
  - OpenAI など外部 API の失敗時は通常は例外で消滅させずフォールバック（例: スコア 0.0）して継続する設計の箇所がある。
- セキュリティ:
  - news_collector は SSRF 対策や XML の安全パーサを使用（defusedxml）し、受信サイズ制限・プライベートIPブロック等を実装。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージ定義, __version__ など)
  - config.py  (環境変数 / 設定管理)
  - ai/
    - __init__.py
    - news_nlp.py       (ニュース NLP / OpenAI 呼び出し / ai_scores への書込)
    - regime_detector.py (1321 MA + マクロニュースで市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント、fetch / save 関数)
    - pipeline.py        (ETL パイプライン / run_daily_etl 等)
    - etl.py             (ETLResult の公開再エクスポート)
    - news_collector.py  (RSS 取得・正規化・raw_news 保存)
    - calendar_management.py (market_calendar 管理・営業日判定)
    - quality.py         (データ品質チェック)
    - stats.py           (zscore_normalize 等)
    - audit.py           (監査ログテーブル定義・初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum, value, volatility 等)
    - feature_exploration.py (forward returns, IC, factor_summary 等)
  - ai/、data/、research/ はそれぞれ目的毎にまとまった実装群

---

## 開発上のヒント

- テスト／CI 環境では自動 .env ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動読み込みを停止できます。
- OpenAI 呼び出しは各モジュールで内部関数をラップしているため、ユニットテストでは該当モジュールの _call_openai_api を patch して外部呼び出しを差し替えてください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています。スキーマ初期化などは transactional オプションに注意。

---

README はここまでです。追加で例えば:
- サンプル .env.example の作成、
- requirements.txt の推奨パッケージ列挙、
- 実行用 CLI スクリプト（例: scripts/run_daily_etl.py）テンプレート、
などを作成することで初期導入がより簡単になります。必要であればそれらも作成します。