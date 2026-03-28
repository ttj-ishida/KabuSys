# KabuSys

日本株向け自動売買プラットフォームのライブラリ（KabuSys）。  
データETL、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ／自動売買の基盤をまとめた Python パッケージです。主な責務は以下：

- J-Quants API から株価・財務・市場カレンダー等の差分取得（ETL）と DuckDB への保存
- RSS ベースのニュース収集／前処理と LLM を使った銘柄別ニュースセンチメントの算出
- ETF とマクロニュースを組み合わせた市場レジーム（bull/neutral/bear）判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引監査ログ（signal → order_request → execution）用の DuckDB スキーマと初期化ユーティリティ
- 設定の環境変数管理（.env 自動読み込み）

設計上の重要点として、バックテストやモデル評価でのルックアヘッドバイアスを避けるため、関数内部で `date.today()` や `datetime.today()` を直接参照しない実装方針が徹底されています。

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制限、リトライ）
  - market_calendar 管理（営業日判定、next/prev/get_trading_days）
  - news_collector（RSS 取得・正規化・SSRF 対策・前処理）
  - news NLP（OpenAI を用いた銘柄別センチメント score_news）
  - market regime 判定（ETF MA200 とマクロニュースを合成して score_regime）
  - データ品質チェック（missing/spike/duplicates/date_consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC 計算 / サマリー統計
- ai/
  - news_nlp.score_news
  - regime_detector.score_regime
- config:
  - 環境変数自動読み込み（.env, .env.local をプロジェクトルート基準で読み込み）
  - settings オブジェクト経由で各種設定取得

---

## 必要条件（想定）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （ネットワークアクセスが必要：J-Quants API、RSS、OpenAI）

requirements.txt をプロジェクトに追加している想定です。以下は例のインストール方法です。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または開発モード
pip install -e .
```

requirements.txt に含める主要パッケージ例:
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは細かなバージョン固定を行ってください）

---

## セットアップ手順

1. リポジトリをクローンしてワーク環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

2. 環境変数（.env）をプロジェクトルートに作成  
   config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（主にテスト用途）。

   .env に設定する代表的なキー（必要に応じて）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API パスワード（本パッケージ内の実装で利用箇所がある想定）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知等を使う機能が将来ある場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

3. DuckDB（データベース）用ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下は代表的な Python API 呼び出し例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を渡して実行します。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントの算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジームの算出（ETF 1321 の MA200 とマクロニュースを合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（専用 DB を作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して監査テーブルが初期化される
  ```

- ファクター計算（Research）例:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク・料金が発生するため、APIキーや料金に注意して実行してください。
- ETL / ニュース / レジーム算出はルックアヘッドバイアスを避ける設計がされています。target_date を正しく指定してください。
- 自動読み込みの .env はプロジェクトルートを基準に検索します。テスト時に自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要なファイル/モジュールのツリー（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数/設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                 - ニュースセンチメント（score_news）
    - regime_detector.py          - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           - J-Quants API クライアント・保存ロジック
    - pipeline.py                 - ETL パイプライン（run_daily_etl 等）
    - etl.py                      - ETLResult 再エクスポート
    - news_collector.py           - RSS 収集・前処理
    - calendar_management.py      - マーケットカレンダー管理（営業日判定等）
    - stats.py                    - 共通統計ユーティリティ（zscore_normalize）
    - quality.py                  - データ品質チェック
    - audit.py                    - 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py          - ファクター計算（momentum/value/volatility）
    - feature_exploration.py      - 将来リターン / IC / サマリー
  - monitoring/ (将来の監視モジュール想定)
  - strategy/ (戦略本体は別モジュールで実装想定)
  - execution/ (発注実装を置く想定)

---

## 開発・テストに関する補足

- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` / `.env.local` を読み込みます。テストで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出し部（news_nlp / regime_detector）では API 呼び出しを差し替えられるように内部呼び出し関数を分離しています。ユニットテストでは `unittest.mock.patch` で `_call_openai_api` をモックできます。
- DuckDB はファイルベースの軽量 DB のため、CI では `:memory:` 接続を使うことでインメモリテストが可能です（例: `duckdb.connect(":memory:")`）。

---

## おわりに

この README はコードベースの公開 API と運用上の注記をまとめた要約です。個別関数の詳細は各モジュール（src/kabusys/**）の docstring を参照してください。設計方針として「ルックアヘッドバイアスを避ける」「外部 API のフェイルセーフ」「DuckDB への冪等保存」などが徹底されています。

不足・追加してほしいドキュメント項目（例: CLI、運用手順、監視・通知ルール、実稼働向け設定例）があれば教えてください。README を拡張します。