# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
J-Quants / kabuステーション / RSS / OpenAI（LLM）を組み合わせ、データ取得（ETL）、品質チェック、ニュースセンチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログスキーマなどのユーティリティを提供します。

注意: 本リポジトリは「システム部品」を提供するライブラリであり、フロントエンドのトレーディング実行 (ブローカー接続) や戦略の完全実装は別途必要です。

---

## 主な特徴

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPXカレンダー等の差分取得と DuckDB への冪等保存
  - レート制御、リトライ、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次ETL 実行エントリポイント（run_daily_etl）
- ニュース収集 / NLP
  - RSS フィード収集、前処理、raw_news / news_symbols への保存（SSRF対策・XML安全化）
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメントスコアリング（score_news）
- 市場レジーム判定
  - ETF 1321 の 200日移動平均乖離とマクロニュースの LLM センチメントを組み合わせた日次判定（score_regime）
- リサーチ（ファクター計算）
  - Momentum / Value / Volatility 等のファクター計算、将来リターン計算、IC / 統計サマリー
- 監査ログ（Audit）
  - signal / order_request / execution を追跡する監査スキーマの初期化ユーティリティ（init_audit_db / init_audit_schema）
- その他ユーティリティ
  - カレンダー管理、統計ユーティリティ（Zスコア正規化）など

---

## 必要な環境変数

以下は最低限セットが必要な環境変数（モジュール内で参照されます）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

その他データベースパスはデフォルトで設定されますが、環境変数で上書き可能です:

- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

.env の自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` があれば自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

前提: Python 3.10+（typing の一部機能で 3.10 以上を想定）。

1. 仮想環境を作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール（最低限の例）:
   ```
   pip install duckdb openai defusedxml
   ```
   実際にはロギングやテスト用パッケージ等もプロジェクトに応じて追加してください。

3. 環境変数を設定:
   - プロジェクトルートに `.env` を作成して必要な値を設定するか、シェルで export / set を使って設定してください。

4. データベースディレクトリの作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリをインポートして利用する際の例です。DuckDB の接続は `duckdb.connect(<path>)` を使います。

- DuckDB 接続サンプル:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると today が使用されます
  result = run_daily_etl(conn, target_date=None)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアを生成（OpenAI API キー必須）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（regime score）を実行:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへアクセス可能
  ```

- ファクター計算（例: momentum）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])
  ```

注意点:
- score_news / score_regime は OpenAI の呼び出しを行います。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しはレート制限を厳守します。大量呼び出し時の制御に注意してください。
- モジュールはバックテストにおけるルックアヘッドバイアスを避ける設計（date の明示的引数、datetime.today() の不使用）になっています。関数の target_date 引数を正しく指定してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 内の主要モジュール一覧（本 README 作成時点の主要ファイル）:

- kabusys/
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
    - (その他: pipeline の ETLResult は etl.py と連携)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py exposes helper functions...
  - (プロジェクトにより strategy, execution, monitoring 等のパッケージが存在する想定)

ファイル群は次の責務に分かれています:
- data/* : データ取得・ETL・品質チェック・カレンダー管理・ニュース収集・DuckDB 保存ロジック
- ai/*   : LLM を用いたニューススコアリング / レジーム判定
- research/* : ファクター計算と統計解析ユーティリティ
- config.py : 環境変数読み込み・設定管理（.env 自動ロードロジックを含む）

---

## 実運用上の注意

- 本ライブラリは実際の注文発行（ブローカーへの注文送信）を直接行うための完全な安全機構を含みません。実際の自動売買で使用する場合は追加のリスク管理、検証、テストを行ってください。
- 機密情報（API トークンなど）は `.env` 等に保存する際、アクセス制御を適切に行ってください。
- J-Quants / OpenAI / kabuステーション 等の API 利用規約・料金を確認して利用してください。
- テスト時は自動環境読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が利用できます。OpenAI / HTTP 呼び出しはモック化してユニットテストを作成してください。

---

もし README に追加したい内容（例: CLI コマンド、具体的な ETL スケジュール設定、詳しい .env フォーマット、ユニットテスト実行方法）があれば教えてください。必要に応じて追記・整備します。