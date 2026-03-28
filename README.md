# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（LLM）評価、マーケットカレンダー管理、ファクター計算、監査ログなどの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない等）
- DuckDB を中心としたローカル DB にデータを保存・参照
- 外部 API 呼び出しは堅牢なリトライとレート制御を備える
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の検証（settings オブジェクト）

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（jquants_client）：株価日足、財務データ、マーケットカレンダーなどの取得と DuckDB への保存（冪等）
  - ETL パイプライン（pipeline / etl）：差分取得、バックフィル、品質チェックの統合実行
  - ニュース収集（news_collector）：RSS の取得・前処理・raw_news への保存（SSRF/サイズ制限/トラッキング除去 等の保護）
  - マーケットカレンダー管理（calendar_management）：営業日判定、next/prev_trading_day、カレンダー更新ジョブ
  - データ品質チェック（quality）：欠損、スパイク、重複、日付不整合の検出
  - 監査ログ（audit）：signal → order_request → execution をトレースする監査テーブルの初期化ユーティリティ
  - 汎用統計ユーティリティ（stats）：Zスコア正規化等

- AI / NLP（kabusys.ai）
  - ニュースごとの銘柄センチメント評価（news_nlp.score_news）：OpenAI を用いたバッチ評価、JSON mode 利用、結果を ai_scores テーブルへ保存
  - 日次市場レジーム判定（regime_detector.score_regime）：ETF(1321)の200日MA乖離とマクロニュースのLLMセンチメントを合成して market_regime に保存

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）：モメンタム / ボラティリティ / バリュー等
  - 特徴量解析（feature_exploration）：将来リターン計算、IC（Spearman）、統計サマリー等
  - 統計ユーティリティの再利用（data.stats）

---

## 前提・必須ソフトウェア

- Python 3.10 以上（型ヒントに | を使用しているため）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パース用）
- そのほか標準ライブラリ以外の依存パッケージ：requests 等は使われていませんが network 関連は urllib を使用

最低限のインストール例（適宜仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## 環境変数（主要）

config.Settings から参照される主要環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を直接呼ぶ場合に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

自動で .env/.env.local をプロジェクトルートから読み込みます（.git または pyproject.toml を基準に検出）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡易 .env 例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env を作成）
   - 先の「環境変数（主要）」セクションを参照して .env を作成してください。

5. DuckDB 初期化（任意：監査ログDB を作る例）
   Python REPL で:
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成されます
   ```

---

## 使い方（代表的な関数例）

以下はライブラリを直接インポートして使う例です。プロダクション用途では各モジュールを呼ぶ CLI / バッチラッパーを作成してください。

- ETL（日次パイプライン）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコアを計算して ai_scores に保存する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored:", count)
  ```

- 市場レジーム判定（regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))
  ```

- ニュース収集（RSS フェッチのみ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"])
  ```

注意点:
- OpenAI を使用する処理（news_nlp / regime_detector）は OPENAI_API_KEY または api_key 引数が必要です。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN が必須です。
- DuckDB のスキーマ（raw_prices, raw_news, ai_scores, market_regime 等）は ETL / schema 初期化ロジックに依存します。実行前にスキーマを作成しておくか、ETL の最初の保存処理で作成されることを確認してください（プロジェクトの schema 初期化処が別にある想定）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py  # ETF MA とマクロニュースを合成して market_regime を作成
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント（取得＆DuckDB 保存）
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - etl.py              # ETLResult の再輸出
    - news_collector.py   # RSS の取得・前処理・挿入
    - calendar_management.py  # 市場カレンダー管理・営業日判定
    - quality.py          # データ品質チェック
    - stats.py            # 汎用統計（zscore_normalize）
    - audit.py            # 監査ログ（テーブル作成 / init）
  - research/
    - __init__.py
    - factor_research.py  # Momentum / Value / Volatility 等の計算
    - feature_exploration.py  # 将来リターン / IC / 統計サマリー 等

各モジュールは docstring と関数説明を豊富に持っています。詳細な利用方法は該当モジュールの docstring を参照してください。

---

## 開発・テスト時のヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。単体テストなどで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部関数をパッチしてテスト可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- news_collector はネットワークに依存するため、fetch_rss/_urlopen をモックするとテストしやすいです。
- J-Quants クライアントは内部でレートリミッタとリトライを実装していますが、実行時は API レート制限に注意してください。

---

もし README に追記してほしい内容（例: CLI コマンド、サンプル DB スキーマ、より詳細なセットアップ手順や Docker 化）があれば教えてください。必要に応じて具体的なサンプルやテンプレートを追加します。