# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI 評価・監査ログ・ETL を統合したライブラリ群です。本リポジトリは以下の機能群をモジュール化して提供します：J-Quants 経由のデータ取得・ETL、ニュース収集と LLM ベースのセンチメント評価、ファクター計算・特徴量解析、マーケットカレンダー管理、監査ログ（トレーサビリティ）など。

---

## 主な特徴（機能一覧）

- データ取得／ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動リフレッシュ対応

- データ品質管理
  - 欠損、重複、スパイク（急変）、日付不整合の検出（quality モジュール）
  - ETL 実行結果を ETLResult に集約

- ニュース収集・NLP
  - RSS フィードからニュースを取得・前処理して raw_news に保存
  - OpenAI（gpt-4o-mini 等）でニュースセンチメント評価（銘柄別 ai_scores へ保存）
  - LLM 呼び出しはバッチ・リトライ・レスポンスバリデーションを実装

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して
    日次で market_regime テーブルにレジームを書き込み（'bull'/'neutral'/'bear'）

- 研究用ユーティリティ（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- 監査（Audit / Tracing）
  - signal_events / order_requests / executions を含む監査テーブル定義と初期化
  - 発注フローの UUID ベースのトレーサビリティをサポート

- カレンダー管理
  - market_calendar を基に営業日判定・次営業日取得・期間の営業日リスト取得
  - J-Quants からの差分更新ジョブ（calendar_update_job）

- 設定管理
  - .env / .env.local /環境変数から自動読み込み（パッケージルート探索）
  - 自動読み込みを無効化するフラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

設計上の共通方針：
- ルックアヘッドバイアス防止（関数内部で datetime.today() を直接参照しない等）
- 冪等性・フェイルセーフ（API 失敗時はスキップやフォールバックで継続）
- 外部ライブラリ依存は最小化（ただし duckdb / openai / defusedxml 等は利用）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

（実際の requirements.txt がある場合はそれを使用してください。なければ上記パッケージを pip でインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - ない場合は最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. パッケージを編集可能インストール（開発時）
   ```
   pip install -e .
   ```

5. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として設定を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_station_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 必要に応じて
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   主な環境変数（settings 参照）
   - JQUANTS_REFRESH_TOKEN（必須）
   - OPENAI_API_KEY（LLM 呼び出しで必須）
   - KABU_API_PASSWORD（kabu ステーション連携）
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
   - KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

---

## 使い方（短いコード例）

以下はライブラリの主要ユースケースのサンプルです。適宜 logger 設定やエラーハンドリングを追加してください。

- DuckDB 接続と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア化（OpenAI API キーは env または引数で指定）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
  print("scored:", count)
  ```

- 市場レジームスコア算出
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査テーブルの初期化（別 DB で監査用に作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を用いて監査ログを操作
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "records")
  ```

注意点：
- OpenAI 呼び出しは API レートやトークン設定に依存します。api_key を関数引数で直接渡すことも可能（テスト用途など）。
- ETL / API 呼び出しはネットワークや外部 API に依存するため、例外処理を適切に行ってください。

---

## 設定・運用メモ

- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を自動検出して `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- 環境（KABUSYS_ENV）
  - 許容値: "development", "paper_trading", "live"
  - settings.is_live / is_paper / is_dev で判定可能

- ログレベル:
  - LOG_LEVEL 環境変数で制御（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）

- データベースパス:
  - DuckDB: settings.duckdb_path（デフォルト data/kabusys.duckdb）
  - SQLite（監視用）: settings.sqlite_path（デフォルト data/monitoring.db）

- Look-ahead バイアス対策:
  - 多くの関数（ETL・NLP・レジーム判定・研究用計算）は内部で datetime.today() を参照せず、target_date を明示的に渡す設計です。バックテストや再現性のため target_date を明示することを推奨します。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要なファイル・モジュール構成です（src/kabusys 以下）：

- __init__.py
- config.py  — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM ベーススコアリング（ai_scores への書き込み）
  - regime_detector.py — 市場レジーム判定（ETF 1321 MA + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー判定・更新ロジック
  - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py            — 日次 ETL パイプライン（prices/financials/calendar の差分取得・品質チェック）
  - stats.py               — 統計ユーティリティ（z-score 等）
  - quality.py             — データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py               — 監査ログ（signal/order/execution）スキーマと初期化
  - jquants_client.py      — J-Quants API クライアント（取得/保存関数）
  - news_collector.py      — RSS ニュース収集・前処理・保存
- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（さらに execution / monitoring / strategy 等のパッケージがある想定ですが、上記はこのコードベースで提供されている主要なモジュールです。）

---

## 補足（運用上の注意）

- J-Quants API のレート制限（120 req/min）をモジュールで制御していますが、大量の並列リクエストを行う場合は注意してください。
- OpenAI 呼び出しはコストとレート制限の観点からバッチ化・キャップを検討してください。
- DuckDB の executemany はバージョンによる挙動差があるため、コード内で空リストを直接投げない等の注意がされています。
- RSS 収集では SSRF・XML Bomb 対策（スキーム検証・プライベートホストチェック・defusedxml）を実装していますが、運用環境ではソースの監査を行ってください。

---

必要であれば、README に以下の情報も追加できます：
- 具体的な requirements.txt（依存バージョン）
- CI / テストの実行方法（pytest 等）
- DB スキーマ定義（raw_prices, raw_news, ai_scores, market_regime 等の CREATE TABLE 例）
- サンプル .env.example

追加希望があればどの項目を展開するか教えてください。