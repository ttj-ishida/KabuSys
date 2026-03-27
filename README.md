# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants や RSS、OpenAI（LLM）を使ったデータ収集・品質チェック・AIセンチメント評価・ファクター算出・監査ログなどを備え、ETL → 研究 → 戦略 → 発注の上流処理をサポートします。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants API）
  - 株価（日足：OHLCV）、財務データ、上場/カレンダー情報の差分取得（ページネーション対応、レート制御、リトライ）。
- ETL パイプライン
  - 差分取得、保存（DuckDB へ冪等保存）、品質チェックの統合実行（run_daily_etl）。
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）。
- ニュース収集／NLP
  - RSS からのニュース収集（SSRF 対策、前処理）、OpenAI を用いた銘柄別センチメント評価（score_news）。
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）。
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターン、IC 計算、Zスコア正規化。
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution まで追跡可能な監査用スキーマ初期化・管理（init_audit_schema / init_audit_db）。
- 設定管理
  - `.env` / `.env.local` または環境変数から設定を自動読み込み（プロジェクトルート検出、読み込み優先度あり）。

---

## セットアップ

前提
- Python 3.10 以上を推奨（型記法や union 型 `X | None` を使用しているため）。
- DuckDB、OpenAI クライアント等の依存ライブラリが必要です。

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（最低限）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください：
   ```bash
   pip install -r requirements.txt
   # または開発時
   pip install -e .
   ```

3. 環境変数／`.env` の準備  
   プロジェクトルート（`.git` または `pyproject.toml` があるディレクトリ）に `.env` または `.env.local` を配置すると、自動で読み込まれます（ただし自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

   必須（少なくとも開発時に必要なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   任意／デフォルトあり
   - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定の場合はこちらを参照）

   .env 例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=./data/kabusys.duckdb
   ```

---

## 使い方（例）

以下はライブラリをインポートして主要処理を呼ぶ基本例です。

- DuckDB 接続を使って ETL を実行（先に dependencies と環境変数を設定してください）:

  Python スクリプト例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl は ETLResult を返します（取得件数・保存件数・品質問題・エラー一覧など）。

- ニュースセンチメントのスコア付与（score_news）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  # 1 を返せば正常終了。market_regime テーブルに結果が書かれます。
  ```

- 監査ログ用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- 研究用ファクター取得:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点
- OpenAI への呼び出しは API キーが必要です。関数には `api_key` 引数を渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- OpenAI 呼び出しは内部でリトライ／フォールバック処理を行いますが、API レートやコストに注意してください。
- テスト時は各モジュールの `_call_openai_api` 等をモックして API コールを差し替えられるよう設計されています。

---

## ディレクトリ構成（主なファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント評価（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch / save 関数）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult 再エクスポート
    - news_collector.py      -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理 / 営業日判定
    - quality.py             -- データ品質チェック（各チェックと run_all_checks）
    - stats.py               -- 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py               -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- IC / forward returns / summaries
  - ai/、research/ などのサブパッケージはそれぞれの公開関数を __all__ でエクスポートしています。

---

## 実装上の設計ノート（重要な挙動）

- .env の自動読み込みはプロジェクトルート（.git か pyproject.toml が存在するディレクトリ）を基準に行います。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env.local` の方が `.env` より優先して読み込まれ、既存 OS 環境変数は保護されます。
- DuckDB への保存は冪等（ON CONFLICT）で実装されており、ETL は部分失敗しても既存データを不必要に消さない設計です。
- OpenAI 呼び出しは複数箇所で行われますが、各箇所とも失敗時にフォールバック（0.0 スコア等）して処理継続する方針です。テスト容易性のため API 呼び出し箇所はモック差し替えが想定されています。
- 日付取り扱いは「ルックアヘッドバイアス防止」の観点から、内部で現在時刻を無条件に参照することを避け、関数呼び出し側が `target_date` を指定する形が基本です。

---

## 開発・貢献

- コードは src/kabusys 配下にモジュール化されています。新しい機能はサブパッケージを追加し、適切に __all__ を更新してください。
- OpenAI / ネットワーク依存部分はモック可能に実装されているため、ユニットテストの作成が容易です。

---

必要であれば、README に実行例（cron/airflow ジョブ、systemd unit ファイル、Slack 通知の使い方等）や .env.example のテンプレート、よくあるトラブルシュート（API 401 時の対処、DuckDB のロック回避など）を追加します。どの情報を優先的に追加しましょうか？