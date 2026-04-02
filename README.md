# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由のマーケットデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、ファクター計算、マーケットレジーム判定、監査ログ（発注 → 約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得 / ETL
  - J-Quants API 経由で株価日足、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS からニュースを収集して raw_news に保存（SSRF 対策・トラッキング除去等）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント（ai_scores へ保存）
  - マクロニュース + ETF（1321）の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査テーブルを DuckDB に初期化・管理
  - order_request_id による冪等性設計
- 設定管理
  - .env / .env.local / OS 環境変数から設定読み込み（自動読み込みは無効化可能）

---

## 必要条件・依存関係

- Python 3.10+
- 必要な主要ライブラリ（プロジェクトの requirements に従ってくださいが、主なもの）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / ニュース RSS

（実行環境に合わせて仮想環境を推奨します）

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化してください。

   ```bash
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   # その他プロジェクト固有の依存は requirements.txt / pyproject.toml を参照
   ```

3. 環境変数を設定します。.env をプロジェクトルートに配置すると自動読み込みされます（優先順位: OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須・推奨）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（個別関数呼び出しで上書き可能）
   - KABU_API_BASE_URL (オプション) — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH (オプション) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (オプション) — デフォルト: data/monitoring.db
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視用）
   - KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル（デフォルト: INFO）

   サンプル .env（README 用例）:

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

## 使い方（代表的な呼び出し例）

以下は Python REPL やスクリプトからの利用例です。各関数は duckdb の接続オブジェクト（duckdb.connect() で取得）を受け取ります。

- DuckDB 接続 & 監査DB初期化

  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # ファイル DB
  conn = init_audit_db("data/audit.duckdb")
  # 既存接続へスキーマ適用
  # conn2 = duckdb.connect("data/kabusys.duckdb")
  # init_audit_schema(conn2)
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を呼んで ai_scores に保存）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み件数: {n_written}")
  ```

- 市場レジーム判定

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究系（ファクター計算）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

注意:
- OpenAI API キーは引数で上書き可能。関数は api_key 引数が None の場合、環境変数 OPENAI_API_KEY を使用します。
- 各処理は「ルックアヘッドバイアス」対策のため、内部で datetime.today() を参照せず、明示的に target_date を渡す設計が採られています。

---

## 自動環境変数読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効化するには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主なファイルと役割）

src/kabusys/
- __init__.py — パッケージ初期化（version 等）
- config.py — 設定 / 環境変数管理（Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント取得 / ai_scores 書込み
  - regime_detector.py — マクロ + MA200 を使った市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理・営業日ロジック
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J-Quants API クライアントと DuckDB 保存ロジック
  - news_collector.py — RSS ニュース収集（SSRF 対策など）
  - quality.py — 品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore 正規化）
  - audit.py — 監査テーブル定義・初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value の算出
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- ai/、research/、data/ 以下にさらに詳細な関数とユーティリティが含まれます。

（実際のプロジェクトルートには pyproject.toml や tests、scripts 等がある想定）

---

## 開発や運用時の注意点

- API キーやトークンは秘匿情報です。公開リポジトリに置かないでください。
- DuckDB に対する大量の INSERT は executemany のチャンク化やトランザクション管理に配慮している設計です。バージョン依存の挙動に注意してください（コード内に互換性対策のコメントがあります）。
- OpenAI 等外部 API の呼び出しはリトライ・タイムアウト制御が組み込まれていますが、レート制限やコスト管理は利用者側でも留意してください。
- NewsCollector は SSRF / 大容量レスポンス等に対する防御を行っていますが、追加のセキュリティ要件がある場合は環境に合わせて調整してください。
- 本プロジェクトはルックアヘッドバイアス対策として「target_date を明示して処理する」方針です。バックテストや再現性のある解析では target_date を必ず明示してください。

---

## さらに詳しい情報 / 拡張箇所

- jquants_client.py: レートリミッタ・トークン自動更新・ページネーション対応が実装されています。J-Quants API の追加エンドポイントを使う場合は同ファイルを拡張してください。
- news_nlp.py / regime_detector.py: OpenAI の JSON Mode を利用した厳密なレスポンスパースを行っています。モデルやプロンプトのチューニングはここで実施できます。
- quality.py: ETL 後の自動品質チェックを呼び出して問題を収集するフローが組み込まれています。運用基準に合わせて閾値やチェック内容を調整してください。

---

質問や追加のドキュメント（例: API の詳細、運用手順、CI/CD、テスト手順など）が必要であれば、どの部分を詳しく書けばよいか教えてください。