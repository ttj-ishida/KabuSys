# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュースNLP（LLM を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを含みます。

## 特徴（機能一覧）
- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数のラップ（settings オブジェクト）
- データ取得・ETL
  - J-Quants API クライアント（レートリミット・リトライ・認証リフレッシュ対応）
  - 日次 ETL（株価・財務・市場カレンダーの差分取得・保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理 / NLP
  - RSS 収集（SSRF 対策、トラッキング除去、テキスト前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores へ書込）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用ユーティリティ
  - ファクター計算（モメンタム/バリュー/ボラティリティなど）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティを担保する DB スキーマ作成ユーティリティ
- その他ユーティリティ
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - DuckDB への冪等保存関数群

---

## 要求事項（推奨環境）
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

実際のプロジェクトでは requirements.txt や pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローンして編集可能インストール（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   # または (依存パッケージを個別にインストール)
   python -m pip install duckdb openai defusedxml
   ```

2. プロジェクトルートに `.env`（および任意で `.env.local`）を用意する。自動ロードの優先順位は:
   OS 環境変数 > .env.local > .env
   自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に引数で指定可能）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合
   - DUCKDB_PATH（省略可、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB 用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/...）

   .env 例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB 用ディレクトリを作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は簡単な Python 例です。実運用ではログやエラー処理を適切に行ってください。

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（OpenAI が必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ma200 とマクロセンチメントの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへアクセス可能
  ```

- ファクター計算 / 研究ユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  from datetime import date

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)
  ```

- カレンダー判定ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  sources = DEFAULT_RSS_SOURCES
  articles = fetch_rss(sources["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

---

## 設定と挙動の補足
- 環境変数は Settings オブジェクト（kabusys.config.settings）から参照できます。
  - settings.jquants_refresh_token, settings.env, settings.log_level, settings.duckdb_path など
- .env の自動ロードはパッケージ内でプロジェクトルートを .git または pyproject.toml を基準に探索して行います。
- OpenAI 呼び出しは gpt-4o-mini を想定した実装になっています（JSON Mode を利用）。
- 外部 API の失敗時はフェイルセーフ挙動で空スコアや中立値を返す実装が多く、全体プロセスを停止しない設計です。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/ 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースNLP（銘柄別スコア・LLM 呼び出し）
    - regime_detector.py  # マクロ + MA200 での市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py         # ETL パイプラインのエントリポイント
    - etl.py              # ETLResult 再エクスポート
    - jquants_client.py   # J-Quants API クライアント + DuckDB 保存
    - news_collector.py   # RSS 収集（SSRF 対策等）
    - quality.py          # データ品質チェック
    - stats.py            # 統計ユーティリティ（zscore_normalize）
    - audit.py            # 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（上に示したファイルが含まれます）

---

## テスト・開発のヒント
- OpenAI 呼び出しやネットワーク依存部分はモック可能な設計（内部の _call_openai_api や _urlopen のモック推奨）。
- 自動 .env ロードを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- DuckDB を :memory: にして単体テストを実行可能（init_audit_db(":memory:") など）。

---

## 貢献・注意点
- 本ライブラリはバックテストや実運用で Look-ahead バイアスに配慮した設計を心がけています。  
  API 呼び出しやデータ取得のタイミングに注意して利用してください。
- 実際に発注する機能（kabuステーション等）を組み合わせる場合は、必ず paper_trading 環境で十分検証を行ってください。

---

必要であれば、README に記載するコマンドやサンプル .env.example、requirements.txt のテンプレートを作成します。どの形式（pyproject/poetry / requirements.txt）での配布を想定しますか？