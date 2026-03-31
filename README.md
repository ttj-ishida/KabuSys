# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLP解析、マーケットレジーム判定、リサーチ用ファクター計算、および監査ログ（注文→約定のトレーサビリティ）を提供します。

主な設計方針として、バックテストでのルックアヘッドバイアス回避、DuckDB を用いた効率的な列指向クエリ、外部API呼び出しに対する堅牢なリトライ/フェイルセーフ処理が盛り込まれています。

---

## 機能一覧

- 環境設定管理
  - `.env` 自動ロード（プロジェクトルート検出: `.git` または `pyproject.toml`）
  - 必須環境変数取得のラッパー（`kabusys.config.settings`）
- データ取得 / ETL（J-Quants）
  - 株価日次（OHLCV）取得・保存（ページネーション・レートリミット対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次ETL パイプライン：差分取得・保存・品質チェック（`run_daily_etl`）
- データ品質チェック（`data.quality`）
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集・NLP（ニュース収集、OpenAI 経由のセンチメント）
  - RSS取得（SSRF対策、gzip対応、トラッキング除去）
  - ニュースを銘柄に紐付けて保存
  - OpenAI（gpt-4o-mini）で銘柄ごと / マクロセンチメントスコアを算出（`ai.news_nlp.score_news`, `ai.regime_detector.score_regime`）
- 研究用（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - シグナル→発注要求→約定までの監査テーブル定義・初期化（冪等・UTCタイムスタンプ）
  - `init_audit_db` / `init_audit_schema` による初期化ユーティリティ

---

## 前提・動作環境

- Python 3.10+
- 主な外部依存パッケージ（プロジェクトにより異なるが最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS）

（実際のプロジェクトでは requirements.txt / Poetry 等で依存管理してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. 仮想環境を作成して依存パッケージをインストール（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須（このコードベースで参照される主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（`ai` モジュール使用時）
   - 任意 / デフォルト:
     - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
     - LOG_LEVEL — ログレベル（`INFO` 等）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマの作成
   - 各モジュールで必要なテーブルはプロジェクトの別モジュール（schema 初期化など）で作成する想定です。監査用 DB は helper 関数で初期化できます（下記参照）。

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。プロセスはアプリやジョブスクリプトから呼び出して運用します。

- DuckDB 接続の取得（settings のデフォルトパスを利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しない場合は今日
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores written: {written}")
  ```

- マーケットレジーム判定（MA + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB 初期化（別ファイルに監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit_duckdb.db")
  # conn_audit は監査テーブルが作成済みの DuckDB 接続
  ```

- RSS を取得してニュースを保存する（news_collector.fetch_rss を利用して、保存処理は別途実装）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), records[:3])
  ```

注意:
- OpenAI を呼ぶ関数はネットワーク/API エラー時にフェイルセーフ（多くは 0.0 を返す / スキップ）設計です。テストでは内部の _call_openai_api をモックしてください。
- ETL / 保存関数は冪等性を考慮してあり、ON CONFLICT や個別 DELETE→INSERT の手順で部分失敗でも既存データを保護します。

---

## よく使う設定・トリック

- 自動 .env ロードを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると config の自動ロードを無効にできます（テスト用途）。
- 環境モード:
  - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかにしてください。`is_live` / `is_paper` / `is_dev` のプロパティで判定できます。
- ログレベル:
  - `LOG_LEVEL` を設定すると `settings.log_level` で利用できます（`DEBUG/INFO/WARNING/ERROR/CRITICAL`）。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み / settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの OpenAI によるセンチメント解析
    - regime_detector.py     — マーケットレジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL（run_daily_etl, run_prices_etl, ...）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py      — RSS 収集 / 前処理
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — zscore_normalize 等ユーティリティ
    - audit.py               — 監査ログ（signal / order_request / executions）定義・初期化
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - research/...              — その他リサーチユーティリティ

---

## トラブルシューティング

- OpenAI / J-Quants の API 呼び出しで頻繁に失敗する
  - ネットワーク、APIキー、レート制限を確認。J-Quants は内部でレートリミット対応済み、OpenAI は retry ロジックがあるもののキーや制限が原因の可能性があります。
- .env が読み込まれない
  - プロジェクトルートが `.git` または `pyproject.toml` のどちらかで検出されます。テスト等で現在のディレクトリ以外を使用する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して手動で環境変数を設定してください。
- DuckDB にテーブルがない
  - ETL / 保存関数は既存テーブルを前提にしています。スキーマ初期化スクリプト（プロジェクト側で管理）を実行、または監査DBなら `init_audit_db` を使用してください。

---

必要があれば、README をプロジェクトの実際の packaging / CI / systemd / cron ジョブ実行手順に合わせて追記できます。どの運用シナリオ（本番/ペーパー/ローカル検証）に合わせたドキュメントが必要か教えてください。