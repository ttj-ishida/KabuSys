# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants や RSS、OpenAI（LLM）などを組み合わせてデータ取得、品質チェック、特徴量作成、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ管理などを提供します。

---

## 概要

主に以下の目的で設計されています。

- J-Quants API から株価・財務・カレンダー等の差分 ETL を安全に実行して DuckDB に保存する
- ニュース（RSS）収集と LLM による銘柄別センチメント（ai_scores）算出
- マーケットレジーム（bull/neutral/bear）の日次判定（ETF 1321 の MA とマクロニュースを合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- 発注〜約定に至る監査ログスキーマ（DuckDB）を初期化・管理する

設計上の特徴として、ルックアヘッドバイアス回避、冪等性（INSERT ... ON CONFLICT）、API リトライ/バックオフ、SSRF 対策、外部サービスキーの環境変数管理などが組み込まれています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足・財務データ・マーケットカレンダー取得（pagination 対応）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の結果を表す ETLResult クラス

- ニュース / NLP
  - RSS 収集（SSRF 対策、URL 正規化、重複防止）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント score_news
  - レスポンス検証・チャンク・リトライロジック

- AI / レジーム判定
  - ETF 1321 の 200 日 MA 乖離と LLM マクロセンチメントを合成して日次レジーム判定 score_regime

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー 等のファクター算出
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化 helpers
  - init_audit_db による DuckDB 初期化

- ユーティリティ
  - 環境変数ロード（.env / .env.local 自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 設定ラッパー（kabusys.config.settings）

---

## 依存関係（主なもの）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （その他）標準ライブラリ

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. ソースを取得して開発環境へインストール（編集可能インストール例）:

   ```bash
   git clone <repository-url>
   cd <repository>
   pip install -e .
   ```

2. 必要な環境変数を設定する（.env をプロジェクトルートに置くことを推奨）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_ENV: environment（development / paper_trading / live）

   自動読み込みについて:
   - パッケージインポート時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. DuckDB 初期化（監査テーブルなど）:

   Python REPL またはスクリプト内で:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
   ```

---

## 使い方（代表的な例）

以下は代表的な Python API の使い方です。実行は仮定の環境変数設定済みを前提とします。

- ETL（日次パイプライン）を走らせる:

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（LLM）を実行して ai_scores テーブルへ書き込む:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か引数で指定
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究系ファクター計算（例: モメンタム）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), "銘柄のモメンタムを計算しました")
  ```

- 監査 DB を初期化する（専用 DB を使う場合）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

テスト／デバッグのヒント:
- OpenAI 呼び出しはモジュール内の _call_openai_api を unittest.mock で差し替えることでモック可能です（score_news, regime_detector 共に設計済み）。
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必要時) — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabu API パスワード
- KABU_API_BASE_URL — kabu API URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視データ）ファイル（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視プロセス関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

settings は kabusys.config.settings 経由で取得できます。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数/設定の読み込みと Settings クラス（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の公開
    - news_collector.py — RSS 収集と前処理
    - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — 市場カレンダー（営業日判定・更新ジョブ）
    - audit.py — 監査ログテーブル定義と初期化（init_audit_db / init_audit_schema）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー 等
  - ai/、research/、data/ 配下にその他補助関数・ユーティリティが実装されています。

---

## 開発・運用の注意点

- ルックアヘッドバイアスへの配慮
  - 多くの関数は datetime.today() / date.today() へ直接依存しない設計（target_date を引数で渡す）です。バックテストや再現性のため、必ず target_date を明示的に与えることを推奨します。

- 冪等性
  - DuckDB への保存処理は ON CONFLICT を使って冪等になっています。部分失敗時の保護（例: ai_scores は対象コードのみ置換）も考慮されています。

- API リトライ・レート制御
  - J-Quants クライアントには固定間隔レートリミッタとリトライ（指数バックオフ）が組み込まれています。OpenAI 呼び出しもリトライ/フェイルセーフ実装があります。

- セキュリティ
  - RSS 収集は SSRF 対策（リダイレクト検査・プライベートアドレスブロック）や defusedxml による XML 安全化を行っています。

---

## サポート / 貢献

バグ報告・機能提案は Issue を作成してください。コード変更は Pull Request を通じてお願いします。テストやドキュメントの追加は歓迎します。

---

これで README の基本案になります。必要であれば、環境変数のサンプル（.env.example）や実行スクリプト（CLI）例、CI / テスト手順、詳細なスキーマ定義（DDL）の追加記載も作成できます。どの追加情報が必要か教えてください。