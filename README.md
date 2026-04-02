# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログ、AI ベースのニュース・レジーム判定、リサーチ用ファクター計算などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムおよびリサーチ基盤を構築するためのモジュール群です。主な役割は次の通りです。

- J-Quants API からの株価・財務・カレンダー取得（Rate limit・リトライ・トークンリフレッシュ対応）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ削除）
- 日次 ETL パイプライン（差分取得、保存、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- AI を使ったニュースセンチメント / 市場レジーム判定（OpenAI）
- 研究（ファクター計算、特徴量探索、統計ユーティリティ）

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API失敗時はスキップ/デフォルト値）」が重視されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API 呼び出し（取得・保存・トークン管理・ページング・レート制御）
  - pipeline: 日次 ETL（prices, financials, calendar）と ETL 結果クラス
  - news_collector: RSS 取得・前処理・raw_news 保存ロジック（SSRF/サイズ上限対策）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査テーブル定義と初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出と ai_scores 書き込み（OpenAI）
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースを組み合わせた市場レジーム判定
- research
  - factor_research: モメンタム / ボラティリティ / バリュー 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー

---

## 要求事項 / 依存パッケージ（例）

最低限必要な Python パッケージ（ピン留めは省略）:
- duckdb
- openai
- defusedxml

※ 実行環境により他のパッケージが追加で必要になる場合があります（標準ライブラリ以外のインポートを確認してください）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   requirements ファイルがある場合はそれを使ってください。なければ最低限:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（os 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。
   - 必須環境変数（Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live（default: development）
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)（default: INFO）
   - OpenAI API: `OPENAI_API_KEY` は ai モジュールを使う場合に必要（関数呼び出し時に引数で渡すことも可能）。

5. データベース初期化（監査ログ等）
   Python から DuckDB 接続を作り監査テーブルを初期化できます:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # 他ファイルパスも可
   ```

---

## 使い方（簡単な例）

以下はライブラリを呼び出す最小例です。実際の運用ではログ設定やエラー処理、環境変数の準備が必要です。

- ETL（日次）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 監査 DB の初期化（別 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続。以降 audit 用テーブルが使用可能。
  ```

注意:
- OpenAI 呼び出しはネットワークと API キーを必要とします。テストでは関数内部の _call_openai_api をモックしてください。
- ETL / DB 書き込み操作はトランザクションで行われますが、部分失敗時の挙動をコードの docstring を参照して確認してください。

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py
- config.py
  - 環境変数と .env 自動ロード、Settings クラス（各種設定値）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析（OpenAI 呼び出し、記事集約、ai_scores 書き込み）
  - regime_detector.py — ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・トークン/レート制御）
  - pipeline.py — ETL パイプライン実装（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news 保存（SSRF 対策、サイズ制御）
  - calendar_management.py — 市場カレンダー管理・営業日判定・カレンダー更新ジョブ
  - quality.py — データ品質チェック（欠損、スパイク、重複、日付整合性）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログテーブル定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー等

補足:
- DuckDB を内部ストレージとして利用する設計です（デフォルトパスは data/kabusys.duckdb）。
- AI モジュールは OpenAI の JSON Mode を利用する想定（gpt-4o-mini を指定）。
- jquants_client は rate limit とトークンリフレッシュに対応し、保存処理は冪等（ON CONFLICT）です。

---

## 注意事項 / 運用上のヒント

- ルックアヘッドバイアス対策が各モジュールに組み込まれています。バックテストでの使用時はデータの取得タイミングに注意してください（例: fetch_listed_info などは取得日時の取り扱いに注意）。
- OpenAI や J-Quants API の失敗はフェイルセーフでデフォルト値（例: macro_sentiment=0.0）にフォールバックする実装が多く、運用時は失敗ログを監視してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して制御できます。

---

この README はコードベースの主要機能と使い方を要約したものです。各関数の詳細な挙動や引数、エラー処理についてはソースコードの docstring を参照してください。必要であれば利用例や CLI ラッパーの追加、requirements.txt の整備も対応します。