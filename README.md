# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、AIベースのニュースセンチメント判定、監査ログ、ETL、カレンダー管理などを包含する日本株自動売買／データプラットフォームのコアライブラリです。本リポジトリのコードは主に DuckDB をデータレイヤに、J-Quants API／RSS／OpenAI API を外部データソースとして利用することを想定しています。

## 特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API 経由で株価（日次 OHLCV）・財務データ・JPX カレンダーを差分取得。ページネーション・認証・リトライ・レート制御を実装。
  - ETL の統合エントリ run_daily_etl により、カレンダー取得 → 株価取得 → 財務取得 → 品質チェック を順次実行。
- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェックを実装。
- ニュース収集（RSS）
  - RSS フィードの取得、URL 正規化、SSRF 対策、被害軽減（サイズ制限、gzip 検査）等を備えた収集器。
- AI（OpenAI）連携
  - ニュースセンチメント（銘柄別）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースのセンチメント合成）: kabusys.ai.regime_detector.score_regime
  - OpenAI の JSON Mode（gpt-4o-mini 等）を用いた堅牢なリトライ・パース処理
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターサマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを担保する監査テーブル群の初期化・管理ユーティリティ
- 設定管理
  - .env / .env.local や環境変数からの設定読み込みを自動化（自動ロードを無効化するフラグあり）

---

## システム要件（推奨）

- Python 3.10 以上（型アノテーションで | を使用しているため）
- 主な依存ライブラリ（必須／代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib、json、logging 等）を多用

必要なパッケージは setup.py / pyproject.toml があればそちらに沿ってください。ない場合は上記を pip でインストールしてください。

---

## 環境変数・設定

主に以下の環境変数を使用します（代表的なもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に環境から参照されます）

自動的にプロジェクトルート（.git または pyproject.toml）を探して `.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

設定が不足している場合は、kabusys.config.Settings の各プロパティが ValueError を投げます。`.env.example` を作成して必要な値を設定してください（プロジェクトに .env.example がある想定です）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従う）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （必要に応じて他のライブラリも追加してください）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成し、必要なキーを設定します。
     例:
       JQUANTS_REFRESH_TOKEN=xxxxx
       OPENAI_API_KEY=sk-xxxxx
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=CXXXXXXX
       KABUSYS_ENV=development

   - テストなどで自動 .env ロードを止めたい場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB ファイルの格納先ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（代表的な利用例）

以下はライブラリをプログラム的に使う基本例です。実行前に .env を正しく設定してください。

- ETL（日次パイプライン）の実行例

  Python スクリプト内で:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると今日が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示したい場合は引数で渡せます。省略時は OPENAI_API_KEY を参照。
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに書き込まれます

- 監査ログ用 DB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 監査テーブル群が作成されます

- 設定参照

  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

注意:
- OpenAI 呼び出しでは API エラー時にフェイルセーフ（スコア 0.0 やスキップ）する設計の箇所があります。ログを確認してください。
- J-Quants API 呼び出しはレートリミット・リトライ・401 トークンリフレッシュを備えています。get_id_token は settings.jquants_refresh_token を利用します。

---

## ディレクトリ構成（主要ファイル）

以下は主要なパッケージ構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（銘柄別）ロジック
    - regime_detector.py   — MA200 とマクロニュースを使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存関数）
    - pipeline.py          — ETL パイプラインと run_daily_etl
    - etl.py               — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py    — RSS ニュース収集
    - quality.py           — データ品質チェック
    - stats.py             — 統計ユーティリティ（zscore 正規化 等）
    - audit.py             — 監査ログ（監査テーブル作成、初期化）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム・ボラティリティ・バリュー等
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

---

## ログ・デバッグ

- settings.log_level を環境変数 LOG_LEVEL で指定できます（デフォルト INFO）。
- 各モジュールが適切に logger を使っています。運用時はロギング設定を行い、ファイルや外部集約に出力してください。

---

## テスト・開発時のヒント

- 自動 .env ロードを止めたいとき:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しや HTTP 通信はテストでモックすることを推奨します（モジュール内の _call_openai_api / _urlopen などは差し替えやすく実装されています）。
- DuckDB はインメモリ ":memory:" を使えば一時 DB を簡単に作成できます（audit.init_audit_db や duckdb.connect で使用可能）。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止: 多くの関数は date.today() / datetime.today() を内部で参照せず、target_date を明示的に渡す設計です。バックテストや再現性を重視するためです。
- すべての外部 API 呼び出しにはリトライロジック・タイムアウト・エラーハンドリングが組み込まれており、失敗時は安全側（部分スキップ・ゼロスコア）で継続する箇所が多いです。
- DuckDB への書き込みは冪等を意識（ON CONFLICT DO UPDATE 等）しているため、再実行でデータが壊れにくくなっています。

---

もし README に追加したい使い方のユースケース（例: コマンドラインのラッパー、Docker 化、CI 用の設定）や、pyproject.toml / requirements.txt の内容があれば教えてください。必要に応じてサンプル .env.example も作成します。