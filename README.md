# KabuSys

日本株の自動売買・データ基盤ライブラリ（部分実装）。  
本リポジトリはデータ取得（J-Quants）、ETL、ニュースNLP／レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを含むモジュール群を提供します。

主な目的は
- データパイプライン（株価・財務・カレンダー）の差分取得と品質チェック
- ニュースを用いた銘柄ごとのAIセンチメントスコア算出
- マーケットレジーム（bull/neutral/bear）の日次判定
- 研究（ファクター計算・将来リターン・IC 等）
- 発注／監査用スキーマ（監査ログ用 DuckDB 初期化）

以下はこのコードベースの概観、セットアップ、簡単な使い方、ディレクトリ構成です。

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出、無効化可能）
  - settings オブジェクト経由で設定取得（J-Quants / kabu / Slack / DB パス / 環境等）

- データ（data パッケージ）
  - J-Quants API クライアント（取得 + DuckDB への保存、ページネーション・リトライ・レート制御）
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS、SSRF対策、正規化）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ定義と初期化（audit モジュール、init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（z-score 正規化など）

- AI（ai パッケージ）
  - ニュースNLP（gpt-4o-mini を想定、JSON Mode を用いたバッチスコアリング）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュース LLM センチメントの結合）

- Research（research パッケージ）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、ランク関数等

- その他
  - DuckDB を前提としたデータ保存・クエリ
  - OpenAI（gpt）呼び出し部分はリトライやフェイルセーフ（失敗時デフォルト値）を持つ
  - テスト容易性を意識した設計（API 呼び出しの差し替えポイントあり）

---

## セットアップ

前提:
- Python 3.9+（型アノテーションにより 3.10 を想定している箇所あり）
- DuckDB, openai, defusedxml 等の依存パッケージ

推奨手順（ローカル開発）:

1. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージをインストール
   - 最低限の依存例:
     - pip install duckdb openai defusedxml
   - その他、テストや開発用途のパッケージを追加してください。

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし、CWD ではなくソースファイル位置から親ディレクトリを遡って `.git` または `pyproject.toml` を検出してプロジェクトルートを決定します）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: .env（最低限必要となるキー）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C12345678
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

4. DuckDB データベース用ディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内での主要な操作例です。

1) 設定と DuckDB 接続
- 例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
- 例:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメント（銘柄別）をスコアリングして ai_scores テーブルへ書き込む
- 例:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

  - OpenAI API キーは環境変数 `OPENAI_API_KEY` または引数 `api_key` で指定可能。
  - テスト時は kabusys.ai.news_nlp._call_openai_api をモックして差し替え可能。

4) 市場レジーム判定（market_regime テーブルへ書き込み）
- 例:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

5) 監査ログ（audit）スキーマの初期化
- 既存 DuckDB 接続に監査テーブルを追加:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 別ファイル（監査専用 DB）を初期化して接続を得る:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

6) 研究用ファクター計算・IC 等
- 例:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  records = calc_momentum(conn, target_date=date(2026,3,20))

ログレベルは環境変数 `LOG_LEVEL` で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロード無効化（1 で無効）

注意: Settings は必須キーの未設定時に ValueError を投げます。

---

## テスト・開発メモ

- OpenAI への実ネットワーク呼び出しはレートやコストが発生するため、テスト時は
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
  を unittest.mock.patch などで差し替えてモックすることを推奨します。

- J-Quants クライアントは内部でトークンキャッシュとレートリミッタを持ち、401 発生時の自動リフレッシュやページネーション対応、リトライ（指数バックオフ）を実装しています。テストでは network 呼び出しをモックしてください。

- news_collector には SSRF 対策や受信サイズ制限、XML の安全なパース（defusedxml）などの保護ロジックがあります。RSS を外部へ投げるテストでは _urlopen の差し替えが可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit (初期化関数)
    - (その他: etl export wrapper 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (参照は __all__ にあるが実実装ファイルが必要)
  - strategy/    (戦略層は別途実装想定)
  - execution/   (実行／ブローカー連携は別途実装想定)

（上記は本リポジトリに含まれる主要モジュールの抜粋です）

---

## 注意事項 / 設計方針の要約

- Look-ahead bias を避ける設計:
  - 各モジュールは date.today() や datetime.today() を直接参照しないよう注意しており、target_date を明示的に受け取ることでバックテスト等で過去のみを参照するようになっています。
- フェイルセーフ:
  - ニュースや LLM 呼び出しに失敗しても処理を継続する設計（デフォルトスコア 0.0 など）を採用しています。
- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT 等で冪等化しています。
- セキュリティ:
  - news_collector で SSRF 対策、defusedxml の使用、レスポンスサイズチェックなどを実施しています。

---

README の内容は随時アップデートしてください。追加で例スクリプト（CLI、systemd timer、Airflow DAG など）のテンプレートを作成したい場合は要件を教えてください。