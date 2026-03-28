# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ（KabuSys）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・データ品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなど、自動売買システムとリサーチ基盤に必要な機能を提供する Python ライブラリです。  
主に以下の機能群を含みます：

- J-Quants からの株価・財務・カレンダーデータ取得と DuckDB への永続化（冪等）
- ニュース収集（RSS）とニュースを用いた銘柄ごとの NLP スコアリング（OpenAI）
- マーケットレジーム判定（ETF + マクロ記事の LLM センチメント合成）
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）と初期化ユーティリティ

設計方針として、ルックアヘッドバイアスを避けること、API 呼び出しに対する堅牢なリトライ・フェイルセーフ、DuckDB を中心とした効率的な SQL 実装を重視しています。

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御・リトライ）
  - pipeline: 日次 ETL 実行 run_daily_etl を含む ETL ロジック
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策、トラッキングパラメータ除去）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日ロジック
  - audit: 監査ログスキーマ定義と初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize など）
- ai:
  - news_nlp.score_news: ニュースを LLM で解析して ai_scores に書き込む
  - regime_detector.score_regime: MA と マクロ記事 LLM を組み合わせて market_regime に書き込む
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数ロード（.env / .env.local の自動ロードを提供）と Settings クラス

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型ヒントに union | を使用）。

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows PowerShell
   ```

3. 依存パッケージをインストール（例）
   必要パッケージ（代表例）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください。

4. 環境変数設定
   プロジェクトルートに `.env`（と必要なら `.env.local`）を置くことで自動ロードされます（モジュール kabusys.config が .env を検索してロードします）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知に使用（プロジェクトで利用する場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   OpenAI を使う機能を使うには:
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に渡すことも可能）

   オプション:
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: デフォルト `data/monitoring.db`
   - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト development）
   - LOG_LEVEL: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`

   .env の一例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース用ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要ワークフローの例）

以下はライブラリの主な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...)=DuckDBPyConnection）を受け取ります。

1. DuckDB に接続
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 監査ログ DB の初期化（監査用 DB を独立して作る場合）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   # audit_conn は初期化済み接続
   ```

3. 日次 ETL 実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

4. ニューススコアリング（OpenAI を使用）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # APIキーは env の OPENAI_API_KEY を使用。必要なら api_key 引数で上書き可。
   n = score_news(conn, target_date=date(2026,3,20))
   print("書き込み銘柄数:", n)
   ```

5. 市場レジーム判定
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   # OpenAI API キーを渡すか、OPENAI_API_KEY を環境変数に設定してください
   score_regime(conn, target_date=date(2026,3,20))
   ```

6. ファクター計算・研究ユーティリティ
   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
   from kabusys.data.stats import zscore_normalize

   target = date(2026,3,20)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target)
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m"])
   znorm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
   ```

7. カレンダー・営業日ユーティリティ
   ```python
   from datetime import date
   from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

   d = date(2026,3,20)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
   ```

注意点:
- LLM 系（news_nlp / regime_detector）は OpenAI API を呼び出します。APIキーの指定やレート・コストに注意してください。
- 多くの関数は「ルックアヘッドバイアス」を避ける実装になっており、内部で date.today() を参照しない設計です。バックテスト用途でも事前に正しいデータ準備が必要です。

---

## ディレクトリ構成

主要なファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NLP スコアリング
    - regime_detector.py           - 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得/保存）
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - etl.py                       - ETL の公開インターフェース（ETLResult）
    - news_collector.py            - RSS ニュース取得・前処理
    - quality.py                   - データ品質チェック
    - calendar_management.py       - 市場カレンダー管理（営業日判定等）
    - audit.py                     - 監査ログスキーマ定義・初期化
    - stats.py                     - 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py           - ファクター計算（momentum/value/volatility）
    - feature_exploration.py       - 将来リターン・IC・統計サマリー等
  - ai/__init__.py
  - research/__init__.py
  - data/etl.py
  - etc.

ドキュメント内の関数は、それぞれのモジュールの docstring と設計方針に従って実装されています。詳細は各ソース内の docstring を参照してください。

---

## 補足・運用上の注意

- 環境変数は OS 環境変数が .env より優先されます。テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants や OpenAI との API 呼び出しはレート制限や料金発生を伴います。開発時は小さな日付範囲やモックを利用してください。
- DuckDB の executemany 等の挙動に依存する箇所があるため、使用する DuckDB のバージョンと互換性に注意してください。
- ニュース収集は SSRF 対策や最大読み込みサイズ制限、トラッキングパラメータ除去などの保護ロジックを備えていますが、運用時はフィードソースの信頼性・ライセンスに注意してください。

---

必要であれば README にサンプル .env.example、requirements.txt、あるいは具体的な運用スクリプト（cron / Airflow / GitHub Actions の例）を追加で作成します。どのフォーマット・詳細を追加したいか教えてください。