# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム基盤です。  
J-Quants / RSS / OpenAI（LLM）等からデータを収集・加工し、ファクター計算・ニュースセンチメント・市場レジーム判定・ETL・データ品質チェック・監査ログなどを提供します。

主な目的は「バックテストに使える高品質なデータ基盤」と「実運用に結びつく監査・発注履歴管理」を両立することです。

---

## 機能一覧（ハイライト）

- ETL パイプライン
  - J-Quants API から株価日足 / 財務データ / 市場カレンダーを差分取得・冪等保存
  - 差分更新・バックフィル・品質チェックを備えた `run_daily_etl`
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、将来日付・非営業日データの検出
- ニュース収集（RSS）
  - RSS 取得・前処理・記事ID正規化（URL 正規化→SHA256）・SSRF 対策・gzip 上限チェック
- ニュース NLP（LLM ベース）
  - 銘柄ごとのニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価して `ai_scores` へ保存
  - バッチ処理・リトライ・レスポンスバリデーション付き
- 市場レジーム判定
  - ETF（1321）200日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）から日次レジーム判定
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリーユーティリティ
- 監査ログ（Audit）
  - シグナル→発注要求→約定 までを追跡する監査テーブル群の初期化ユーティリティ
- J-Quants クライアント
  - レート制御、トークン自動リフレッシュ、リトライ、DuckDB への冪等保存

---

## セットアップ手順

前提: Python 3.10 以上を想定（typing の一部に | 型等を使用）。

1. リポジトリをクローン／プロジェクトディレクトリへ移動

2. 依存パッケージをインストール（例）

   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. パッケージの開発インストール（任意）

   ```
   pip install -e .
   ```

4. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数:
     - `JQUANTS_REFRESH_TOKEN` — J-Quants リフレッシュトークン（ETL 用）
     - `SLACK_BOT_TOKEN` — Slack 通知を使う場合の Bot トークン
     - `SLACK_CHANNEL_ID` — Slack チャンネル ID
     - `KABU_API_PASSWORD` — kabu ステーション API パスワード（発注連携を行う場合）
     - `OPENAI_API_KEY` — OpenAI 呼び出し用（ニュース/レジーム判定/その他）
   - 任意 / デフォルト値あり:
     - `KABU_API_BASE_URL` — kabuAPI の base URL（デフォルト http://localhost:18080/kabusapi）
     - `DUCKDB_PATH` — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
     - `SQLITE_PATH` — 監視用 SQLite 等（デフォルト `data/monitoring.db`）
     - `KABUSYS_ENV` — `development` / `paper_trading` / `live`（デフォルト `development`）
     - `LOG_LEVEL` — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）

5. DB 関係の初期化
   - 監査ログ（audit）用 DB を作る場合:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 通常は `settings.duckdb_path` を使って接続:
     ```py
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（主要な例）

- 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）

  ```py
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア（OpenAI API キーは環境変数 `OPENAI_API_KEY` を利用可）

  ```py
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（MA200 + マクロニュース）

  ```py
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存 DuckDB にテーブル群を追加）

  ```py
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  init_audit_schema(conn, transactional=True)
  ```

- ファクター / リサーチ系ユーティリティ

  - モメンタム計算:
    ```py
    from kabusys.research.factor_research import calc_momentum
    records = calc_momentum(conn, date(2026, 3, 20))
    ```
  - Z-score 正規化:
    ```py
    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
    ```

注意点:
- OpenAI の呼び出しは外部 API のため失敗（RateLimit、ネットワーク等）を許容する設計です。失敗時はデフォルト値でフォールバックする箇所があります（例: マクロセンチメント=0.0）。
- テスト時には各モジュール内の `_call_openai_api` をモックすることで API コールを差し替え可能です。

---

## .env 自動読み込み

パッケージはプロジェクトルート（`.git` または `pyproject.toml` が存在するディレクトリ）を自動検出し、`.env` と `.env.local` を順に読み込みます。

- 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
- 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ処理・保存）
  - regime_detector.py — 市場レジーム判定ロジック
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 収集 / 前処理 / DB 保存ロジック
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — 汎用統計ユーティリティ（Z-score）
  - audit.py — 監査ログ（DDL・初期化）
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
- ai/、research/、data/ の各モジュールは DuckDB 接続を受け取り純粋にデータ処理を行う設計で、発注 API などの副作用は最小化されています。

---

## 開発上の注意 / 設計方針まとめ

- ルックアヘッドバイアス対策: 各モジュールは `datetime.today()` を直接参照せず、明示的な `target_date` を用いる設計です。
- 冪等性: J-Quants からの保存は ON CONFLICT DO UPDATE を使い冪等保存を行う。
- フェイルセーフ: 外部 API の失敗は基本的にログ記録とフォールバックで継続する（例外を全体に波及させない箇所多数）。
- セキュリティ: RSS 収集では SSRF 対策、defusedxml を使用した XML パース、受信バイト上限などを実装。
- テスト支援: OpenAI 呼び出し等はモック可能な内部関数に分離。

---

## よくある質問 / トラブルシューティング

- Q: OpenAI キーがないと動きませんか？  
  A: ETL（J-Quants）や多くのデータ処理は OpenAI に依存しません。news_nlp / regime_detector 等の LLM 依存機能のみ `OPENAI_API_KEY` が必要です。

- Q: .env が読み込まれない／テストで無効化したい  
  A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

- Q: DuckDB に書き込み権限エラーが出る  
  A: `settings.duckdb_path` の親ディレクトリが存在するか、プロセスに書き込み権限があるかを確認してください。`init_audit_db` は親ディレクトリを自動作成します。

---

この README はコードの主要機能・使い方を簡潔にまとめたものです。詳細な実装や設計背景は各モジュール（src/kabusys 以下）の docstring を参照してください。必要であれば、導入ガイド（インフラ・CI 設定、運用手順）や API ドキュメントのテンプレートも作成できます。