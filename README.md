# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

この README はコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、ニュースの NLP（LLM を使ったセンチメント評価）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（トレーサビリティ）などを包含する自動売買プラットフォーム向けのライブラリ群です。

主な設計思想・特徴：
- DuckDB を用いたローカルデータプラットフォーム（ETL → 保存 → 解析）
- J-Quants API からの差分取得（認証トークン管理、レートリミット、リトライ）
- ニュース収集時の SSRF 防止・前処理・冪等保存
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・市場レジーム判定（JSON-mode を利用）
- 品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ
- ルックアヘッドバイアス防止を前提とした設計（内部で date.today()/datetime.today() を直接参照しない等）

---

## 機能一覧（ハイライト）

- 環境設定管理
  - settings オブジェクト（`kabusys.config.settings`）で主要な環境変数を参照
  - .env / .env.local の自動ロード（ルート判定：.git または pyproject.toml）
  - 自動ロード無効化用フラグ：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ ETL
  - 日次 ETL（prices / financials / market_calendar）: `kabusys.data.pipeline.run_daily_etl`
  - 差分取得・backfill 対応、品質チェック統合
  - J-Quants API クライアント: `kabusys.data.jquants_client`（認証・ページネーション・保存ユーティリティ）

- データ品質チェック
  - 欠損（OHLC）、スパイク、重複、日付整合性検査: `kabusys.data.quality`

- ニュース収集 / NLP
  - RSS 取得と前処理、raw_news への冪等保存: `kabusys.data.news_collector`
  - OpenAI を使った銘柄ごとのニュースセンチメント: `kabusys.ai.news_nlp.score_news`
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定: `kabusys.ai.regime_detector.score_regime`

- 研究（Research）
  - ファクター計算（momentum / volatility / value）: `kabusys.research.factor_research`
  - 将来リターン計算・IC・統計サマリー: `kabusys.research.feature_exploration`
  - z-score 正規化ユーティリティ: `kabusys.data.stats.zscore_normalize`

- 監査ログ（Audit）
  - signal → order_requests → executions のスキーマ定義と初期化関数: `kabusys.data.audit.init_audit_db` / `init_audit_schema`

---

## セットアップ手順

1. Python バージョン
   - Python 3.9+（ソースは型ヒントに `|` を使用しているため 3.10 推奨）

2. リポジトリをクローンしてインストール（開発環境）
   - 例:
     ```bash
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb openai defusedxml
     # 開発インストール（パッケージ化されている場合）
     pip install -e .
     ```
   - 依存パッケージ（最低限）:
     - duckdb
     - openai
     - defusedxml

   - 実行環境では標準ライブラリの urllib 等も使用します。

3. 環境変数（.env）の準備
   - プロジェクトルートに `.env` と（必要に応じて）`.env.local` を配置できます。
   - 自動ロードの優先順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   - 主要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、jquants_client が使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
     - OPENAI_API_KEY: OpenAI を利用する場合（news_nlp / regime_detector）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知連携を使う場合（任意）
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
     - KABUSYS_ENV: 環境（development, paper_trading, live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - PAPER_FILL_MODE: paper_trading の場合のモック約定動作（instant|partial|never|reject）

   - .env の例（テンプレート）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_pass
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要な例）

以下はライブラリの主要な公開 API の利用例です。実際には適切なエラーハンドリング・ログ設定を行ってください。

- DuckDB 接続の確立（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が使われる
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコア化して ai_scores テーブルへ保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} codes to ai_scores")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- ファクター計算・研究ユーティリティ
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)
  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  ```

注意点：
- OpenAI 呼び出しを行う関数は api_key 引数を受け取ります（引数が None の場合は環境変数 OPENAI_API_KEY を参照します）。
- 多くの処理は「ルックアヘッドバイアス防止」のために target_date を明示的に受け取る設計です。バックテストや再現性のためには日付を明示的に渡してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants 認証用リフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー（news_nlp / regime_detector 等で使用）
- KABU_API_PASSWORD: kabu API パスワード（発注関連）
- KABUSYS_ENV: 実行環境。いずれか: development / paper_trading / live
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant/partial/never/reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（主なファイルとモジュール）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込みと settings オブジェクト（自動 .env ロード）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM センチメントスコアリング（ai_scores）
  - regime_detector.py  — マクロセンチメント + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py         — 日次 ETL パイプラインと個別 ETL 関数
  - etl.py              — ETL 型の再エクスポート（ETLResult）
  - news_collector.py   — RSS 取得、前処理、raw_news への保存
  - quality.py          — データ品質チェック
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py            — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py  — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- research パッケージは zscore_normalize を利用している
- その他: strategy / execution / monitoring 等パッケージを想定した __all__（トップレベルでエクスポート）

（注）README で網羅しているのは主要コンポーネントです。詳細な関数シグネチャやテーブルスキーマは各モジュールの docstring とソースコードを参照してください。

---

## 動作設計に関する重要な注意点

- ルックアヘッドバイアス対策: 多くの関数は内部で現在時刻を直接参照せず、明示的な target_date を受け取ることでバックテスト再現性を確保しています。バックテストや再現性を必要とする場合は target_date を必ず指定してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）から探索します。CI やテスト環境で予想外の挙動になる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はネットワークエラー・レート制限に対してリトライやフォールバック（スコア=0）を行うようになっています。運用時は API コストとレート制限に注意してください。
- J-Quants API はレート制限とトークン期限があるため、jquants_client は内部でレート制御とトークンの自動リフレッシュ処理を実装しています。

---

## 貢献・開発メモ

- 単体テストでは外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることを想定しています。モジュール内の `_call_openai_api` や `kabusys.data.news_collector._urlopen` などはテスト用に差し替えられるように設計されています。
- DuckDB に保存する際は ON CONFLICT / executemany の挙動に注意（空リストを渡せない制約等）。pipeline モジュールではこの点に配慮しています。

---

必要に応じて、README に追記したい具体的な利用シナリオ（例: バックテスト用のデータ準備手順、監視・運用フロー、発注フローのサンプル）を教えてください。コードの特定モジュールの詳しい使用例も作成します。