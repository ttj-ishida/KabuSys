# KabuSys

KabuSys は日本株のデータプラットフォームと研究／自動売買基盤の小規模なライブラリ群です。  
主に以下を提供します。

- J-Quants API と連携したデータ ETL（株価・財務・マーケットカレンダー）
- ニュース収集・NLP に基づく銘柄センチメント付与（OpenAI を利用）
- 市場レジーム判定（ETF + マクロニュースの融合）
- ファクター計算・特徴量探索（研究用途）
- データ品質チェック、監査ログ（トレーサビリティ）
- kabu ステーション経由の実行／モニタリング（将来的な拡張を想定）

バージョン: 0.1.0

---

## 主な機能一覧

- data
  - ETL：日次差分で J-Quants から株価・財務・カレンダーを取得し DuckDB に保存（冪等処理）
  - news_collector：RSS からのニュース取得と raw_news への保存（SSRF や gzip 等の安全対策あり）
  - quality：欠損・重複・スパイク・日付不整合チェック
  - jquants_client：API リクエスト、レート制御、リトライ、トークン自動リフレッシュ、DuckDB への保存関数
  - audit：シグナル→発注→約定の監査スキーマ初期化 / 操作
  - calendar_management：マーケットカレンダー管理と営業日判定ヘルパー
  - stats：汎用統計ユーティリティ（zscore など）
- ai
  - news_nlp.score_news：ニュースをまとめて OpenAI に投げ、銘柄ごとの ai_score を作成して ai_scores テーブルへ保存
  - regime_detector.score_regime：ETF（1321）の MA200 乖離＋マクロニュースセンチメントから市場レジームを判定して market_regime に保存
- research
  - factor_research：モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration：将来リターン計算、IC（スピアマン）、統計サマリーなど
- 設定管理
  - config.Settings：.env または環境変数から各種キー/パス/フラグを読み込み（自動 .env ロード機能あり）

---

## セットアップ手順

※ ここではローカル開発環境を想定した手順を示します。

1. Python 仮想環境の作成（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要な主な依存:
     - duckdb
     - openai
     - defusedxml
   - 通常はプロジェクトの pyproject.toml / requirements.txt からインストールします。
     例（開発時）:
     - pip install -e .[dev]
     または最低限:
     - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を用意できます。パッケージは起動時に自動でプロジェクトルートの `.env` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  (AI 機能を使う場合)
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=INFO|DEBUG|... (default: INFO)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   例: .env.example
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（監査ログなど）
   - 監査ログ用 DB の初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # これで監査テーブル群が作成されます
     ```

---

## 使い方（主要な利用例）

以下は簡単な Python からの利用例です。DuckDB を使う想定です。

1. 設定を参照する
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   ```

2. DuckDB 接続を開いて日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())
   ```

3. ニュース NLP スコアリング（OpenAI を使用）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   # env OPENAI_API_KEY が設定されていれば api_key 引数は不要
   written = score_news(conn, target_date=date(2026,3,20))
   print(f"wrote {written} ai_scores")
   ```

   - テスト時は kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え可能です。

4. 市場レジーム判定
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026,3,20))  # OpenAI API key は環境変数か引数で指定
   ```

5. ファクター計算・研究系ユーティリティ
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
   from kabusys.data.stats import zscore_normalize

   conn = duckdb.connect(str(settings.duckdb_path))
   target = date(2026,3,20)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target)
   ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
   summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
   ```

6. データ品質チェック
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)
   ```

---

## 主要 API / 注意点

- 環境読み込み
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml で判定）にある `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI 呼び出し
  - news_nlp と regime_detector はそれぞれ内部で OpenAI Chat Completions（JSON mode）を呼び出します。テスト容易性のため `_call_openai_api` をモック可能です。
  - API エラー時はフェイルセーフでスコアをスキップまたは 0.0 にフォールバックする設計です（例外を上位に投げない箇所が多い）。

- J-Quants API
  - レート制限（120 req/min）を固定間隔スロットリングで守る実装があります。401 はリフレッシュトークンで自動更新します。
  - ETL は差分取得 + バックフィル（既存データの数日前から再取得）で後出し修正を吸収します。

- DuckDB
  - デフォルトの DB パスは settings.duckdb_path（data/kabusys.duckdb）。
  - executemany に空リストを渡すとエラーになるバージョンへの互換考慮があるため、関数側で空チェックしています。

- セキュリティ
  - news_collector は SSRF 対策、XML の defusedxml 利用、レスポンスサイズ制限、tracking パラメータ除去などの対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys 以下）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult エクスポート)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/research/*（ファクター・探索用）
- そのほか（strategy, execution, monitoring）パッケージが将来的に含まれる想定（__all__ に宣言済み）

---

## 開発／テストに関するメモ

- 設定や外部 API を用いる処理は、関数ごとに API 呼び出しをラップしているためモック差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- 自動 .env 読み込みを無効化してテストしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使ったテストでは ":memory:" を DB パスに渡してインメモリ DB を利用できます（例: init_audit_db(":memory:")）。

---

## ライセンス / 貢献

この README ではライセンス情報は含めていません。実際の配布リポジトリでは LICENSE ファイルを設定してください。  
貢献やバグレポートはリポジトリの Issues / Pull Requests にて受け付けてください。

---

必要であれば README にサンプル .env.example、さらに詳細な API リファレンス（各関数の引数/戻り値の例）を追記します。どの情報を優先して追加しますか？