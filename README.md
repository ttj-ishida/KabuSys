# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）→ DuckDB への永続化 → 品質チェック → 研究・特徴量計算 → 発注・監査というワークフローを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構成する以下の主要機能をモジュール化しています。

- J-Quants API からの株価・財務・カレンダー取得（rate limiting / retry / token refresh 対応）
- RSS ベースのニュース収集とテキスト前処理（SSRF 対策・トラッキングパラメータ除去）
- DuckDB ベースのデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索（将来リターン・IC 計算）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 各種ユーティリティ（Zスコア正規化、カレンダー管理、品質チェックなど）

設計方針は「冪等性」「Look-ahead bias の回避」「外部 API 呼び出しの安全化」「テスト容易性の確保」です。

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ）
  - fetch / save 機能: 日足、財務諸表、マーケットカレンダー
- data.news_collector
  - RSS 取得（gzip 解凍、XML パースに defusedxml を利用）
  - URL 正規化、記事 ID 化、記事保存（raw_news）、銘柄抽出・紐付け
  - SSRF・応答サイズ・gzip bomb 等の防御
- data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- data.pipeline / data.etl
  - 日次 ETL（差分取得・backfill・品質チェック）
  - run_daily_etl による一括処理
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック
  - QualityIssue 型で検出結果を返す
- data.calendar_management
  - market_calendar を用いた営業日判定・次営業日/前営業日取得・カレンダー更新バッチ
- data.audit
  - シグナル / 発注要求 / 約定 を保存する監査ログの DDL と初期化機能
- research.factor_research
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
- research.feature_exploration
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー
- data.stats / data.features
  - zscore_normalize（クロスセクション正規化）

---

## 動作要件

- Python 3.10 以上（型注釈の union types を使用）
- 必須（利用する機能により異なります）パッケージ:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数 / 設定

設定は .env（および .env.local）または OS 環境変数から自動ロードされます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

主な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（API 利用時に必要）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等で使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot Token
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

.env のテンプレートはプロジェクトルートに .env.example を置く想定です。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. .env を作成（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な例）

- 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブ（RSS から記事を収集して raw_news に保存、銘柄紐付け）

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コード集合（例）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- ファクター計算（モメンタム等）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records: list of dict with mom_1m, mom_3m, mom_6m, ma200_dev
  conn.close()
  ```

- 将来リターン・IC 計算

  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
  # factor_records は事前に calc_momentum 等で作成したもの
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- DuckDB への監査スキーマ追加

  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 推奨ワークフロー（運用例）

1. nightly Cron / CI で:
   - init_schema（初回のみ）
   - run_daily_etl（J-Quants からの差分取得 + 品質チェック）
   - calendar_update_job（必要に応じて）
   - news_collector.run_news_collection（取得・銘柄紐付け）
2. 研究環境で:
   - DuckDB を読み込み、research.* の関数でファクター/バックテスト/特徴量探索
3. 発注フロー（paper_trading / live）:
   - strategy 層で signals を生成 → audit / order_requests に記録 → execution 層で証券会社連携

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py      — RSS 収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義 & init_schema/get_connection
    - pipeline.py            — ETL 実装（run_daily_etl 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - features.py            — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - strategy/
    - __init__.py            — 戦略関連モジュールのプレースホルダ
  - execution/
    - __init__.py            — 発注実行関連のプレースホルダ
  - monitoring/
    - __init__.py            — 監視 / モニタリング関連のプレースホルダ

---

## 注意事項 / 補足

- 環境変数は機密情報を含みます。Git 管理下に置かないようにしてください（.gitignore に .env を追加）。
- J-Quants の API レートは考慮されていますが、運用時は API 利用ポリシーに従ってください。
- 実際の発注（kabu API 等）を行うパスは本リポジトリで部分的に想定されていますが、証券会社 API の実装・テストは慎重に行ってください（模擬環境での十分な検証を推奨）。
- Python のバージョンは 3.10 以上を推奨します。

---

## 貢献・開発

バグ報告・機能提案は Issue へお願いします。プルリクエストは小さな単位で、テスト（可能な場合）とともに送ってください。

---

以上が KabuSys の README です。用途に応じてサンプルスクリプトや .env.example、requirements.txt を追加すると導入がスムーズになります。必要であれば README に具体的な API 使用例や運用手順（systemd / cron / Airflow など）を追記します。どの部分を詳しく載せたいか教えてください。