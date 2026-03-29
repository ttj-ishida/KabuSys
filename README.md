# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のコアライブラリです。本リポジトリはデータ収集（ETL）、データ品質チェック、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、システムの中核となる機能群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB をデータ格納に利用し、SQL + Python の組合せで処理
- 外部 API 呼び出し（J-Quants / OpenAI 等）は失敗時にフェイルセーフ動作を行う（部分失敗を許容）
- 冪等性を重視（DB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー、上場情報）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質管理
  - 欠損、重複、スパイク（急騰・急落）、日付不整合のチェック
- 市場カレンダー管理
  - 営業日判定、翌営業日/前営業日取得、期間内営業日列挙
  - カレンダー夜間バッチ更新ジョブ
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF・大容量対策・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック
- ニュース NLP / AI
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に格納（バッチ/チャンク処理、リトライ）
  - マクロニュース + ETF（1321）200日移動平均乖離を合成した市場レジーム判定（bull/neutral/bear）
- リサーチ系ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit / Tracing）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化ユーティリティ
  - 監査DB 初期化関数（DuckDB）

---

## 必要条件（想定）

- Python 3.10+
- ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース 等）
- （オプション）kabuステーション API との接続情報（発注などを行う場合）

実際のパッケージ依存関係はプロジェクトの packaging / requirements を参照してください。以下は代表的なインストール手順例です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際はプロジェクトに requirements.txt または pyproject.toml があればそちらを使用してください。

4. 環境変数設定
   - プロジェクトルートに `.env` と `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能）。
   - 必須環境変数（コード内 Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token で使用）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 追加設定:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"
     - OPENAI_API_KEY — OpenAI API を使う処理で省略時に参照される

   例 `.env`（必要に応じて `.env.local` に機密値を置く）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=...
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な API / 実行例）

以下は Python REPL やスクリプトから利用する簡単な例です。DuckDB 接続は duckdb.connect(<path>) を使用します。

- ETL（日次パイプライン）を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア付け（ai_scores 生成）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```
  - OpenAI API キーを関数引数 api_key に渡すか、環境変数 OPENAI_API_KEY を設定してください。

- 市場レジーム判定（ETF 1321 + マクロニュースの合成）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を使って監査テーブルが利用可能
  ```

- J-Quants クライアント（直接使う場合）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  # get_id_token() は settings.jquants_refresh_token を使って取得する
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

注意点:
- 多くの関数は外部 API（J-Quants / OpenAI）や DB スキーマ（raw_prices, raw_financials, raw_news 等）が前提です。実行前にスキーマ作成や必要データの準備を確認してください。
- OpenAI 呼び出し部はリトライやフェイルセーフ設計がされていますが、APIキーや料金に注意して実行してください。

---

## 環境設定の自動ロードについて

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を親ディレクトリで探索）を見つけると、`.env` と `.env.local` を自動で読み込みます（既存 OS 環境変数は保護されます）。
- 自動読み込みを無効にするには環境変数を事前に設定してください:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

簡略化したツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日ロジック
    - etl.py                 — ETL インターフェース再エクスポート
    - pipeline.py            — ETL パイプラインの実装（run_daily_etl 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py      — RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（上記は主要ファイルのみ抜粋。実際のリポジトリには追加モジュールやテストが含まれる可能性があります）

---

## 開発 / テストに関するヒント

- OpenAI 呼び出しや HTTP 呼び出しはモックしやすいように内部で関数を切り出してあります（ユニットテストでは patch して差し替え可能）。
- DuckDB はメモリ上（":memory:"）でも使用可能なのでテスト用に便利です。
- .env の自動読み込みはテストによる環境の汚染を避けるために無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 注意事項

- 実際に発注を行う機能（kabuステーション連携等）を有効にする場合は十分な検証とリスク管理を行ってください。本コードベースは発注を行う環境向けの補助ツールを提供しますが、実運用では追加の安全対策（ポジション管理、二重送信防止、監査ログ確認など）が必須です。
- 外部 API の料金や利用制限に注意してください（OpenAI / J-Quants 等）。

---

この README はコードコメントや関数 docstring を元に作成しています。詳細な利用方法や環境構築手順はプロジェクトのトップレベルドキュメント（pyproject.toml / docs / CONTRIBUTING 等）がある場合はそちらを優先してください。追加の説明やサンプルが必要であれば教えてください。