# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データの収集（J-Quants、RSS）、ETL、データ品質チェック、機械学習向けファクター計算、LLM を用いたニュースセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）など、アルゴリズム取引・リサーチに必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価日足・財務データ・JPX カレンダーを差分取得・保存（冪等）
  - RSS からのニュース収集（SSRF対策、トラッキングパラメータ除去）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合などの自動チェック
- AI ユーティリティ
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント分析（ai.news_nlp.score_news）
  - マクロ指標（ETF 1321 の MA）と LLM センチメントを合成した市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ／ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリー
- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティを保持する監査テーブル定義・初期化ユーティリティ
- 設定管理
  - .env ファイルおよび環境変数からの設定読み込み（プロジェクトルート検出あり）
  - 自動ロード無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 依存関係（代表例）

主に以下パッケージを使用しています（プロジェクト側で requirements.txt を用意してください）：

- Python 3.9+
- duckdb
- openai
- defusedxml

（標準ライブラリの urllib、json、datetime 等も多用）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化：

   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール（requirements.txt がある場合）：

   ```
   pip install -r requirements.txt
   ```

   または主要ライブラリを個別に：

   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを開発モードでインストール：

   ```
   pip install -e .
   ```

4. 環境変数を設定する（.env をプロジェクトルートに置くと自動で読み込まれます。自動読み込みは .git または pyproject.toml を基準に有効化されます。テスト時に無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）：

   例: `.env`（必須項目）
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch/save 系で必要）
   - OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
   - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
   - SLACK_*: 監視等で Slack 通知を使う場合
   - KABUSYS_ENV: development / paper_trading / live（有効な値）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（代表的な API）

以下は Python スクリプト内で利用する想定です。DuckDB 接続を渡して各ユーティリティ関数を呼びます。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）：

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（データ取得・保存・品質チェック）：

  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date を指定してもよい
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（ai_scores テーブルへ保存）：

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は OPENAI_API_KEY を参照
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ保存）：

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算（返り値は dict のリスト）：

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

- 将来リターン・IC・統計サマリ：

  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 監査ログ（audit）スキーマ初期化：

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn に対して:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- J-Quants クライアント直接利用（テストや詳細制御が必要な場合）：

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

---

## 設定（環境変数の主要一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
- KABU_API_PASSWORD: kabu API のパスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視DBパス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行監視で使用する PID ファイル（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします（ただし OS 変数は保護）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の公開
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py      — ファクター（Momentum/Value/Volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ

（実際のファイルは src/kabusys 以下にあります）

---

## 注意・運用上のポイント

- Look-ahead バイアス対策
  - 多くの関数は内部で date.today() 等に頼らず、呼び出し側が指定した target_date の過去データのみを参照する設計になっています。バックテスト用途では target_date の扱いに注意してください。
- 冪等性
  - J-Quants の保存処理や ETL は ON CONFLICT DO UPDATE 等で冪等化されています。部分失敗時に既存データを不要に上書きしないよう設計されています。
- OpenAI 呼び出し
  - レスポンスのパース失敗や API エラー時はフェイルセーフ（スコアを 0 にフォールバック、または該当チャンクをスキップ）する実装になっています。ただし APIキーの設定は必須です。
- セキュリティ
  - news_collector は SSRF 対策や XML パースに defusedxml を利用するなど安全策を取っています。RSS ソースの運用や外部 URL の扱いには注意してください。

---

## よくある操作例（スニペットまとめ）

- 開発用 DB で日次 ETL を実行：

  ```bash
  python -c "from datetime import date; import duckdb; from kabusys.data.pipeline import run_daily_etl; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn, target_date=date(2026,3,20)).to_dict())"
  ```

- OpenAI キーを引数で渡してニューススコアを算出：

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026,3,20), api_key="sk-...")
  ```

---

## 開発・テスト

- テスト実行やユニットテストからは環境変数の自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や外部 API 呼び出しはモック可能に設計されている箇所が多く、unittest.mock による差し替えでテスト可能です（例: kabusys.ai.news_nlp._call_openai_api をモック）。

---

必要であれば README に以下を追加できます：
- 具体的な .env.example ファイルのテンプレート
- CI / デプロイ手順（systemd / supervisor での実行例）
- さらに詳しい API リファレンス（各関数の引数/返り値一覧）
必要でしたら指示ください。