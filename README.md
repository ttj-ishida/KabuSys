# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants などの外部データソースからデータを取得して DuckDB に保存し、特徴量計算・品質チェック・ETL パイプライン・ニュース収集・監査ログ等を提供します。

主な設計方針は次の通りです。
- DuckDB を主要な永続ストレージとして利用（冪等な INSERT、ON CONFLICT を活用）
- Look-ahead bias を防ぐために取得時刻（fetched_at）を記録
- API 呼び出しはレート制御・リトライ付きで安全に行う
- Data / Research / Execution 層を分離し、実運用（本番/ペーパー）を考慮した設定管理

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 自動読み込みと型・値検証（kabusys.config）
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます
  - 自動読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダー取得
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ対応
  - DuckDB への保存ユーティリティ（冪等保存）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - インデックス作成、初期化ユーティリティ
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分取得 + バックフィル）
  - 市場カレンダー先読み、品質チェックとの統合（日次 ETL）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue オブジェクトで返却）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理（URL除去・正規化）、記事ID生成（正規化URL の SHA-256 prefix）
  - SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - シグナル→注文要求→約定までトレース可能な監査テーブル群
  - すべての TIMESTAMP を UTC に固定する等の運用配慮

---

## 前提・依存関係

- Python >= 3.10（PEP 604 の型表記などを使用）
- 必要パッケージ（主要なもの）
  - duckdb
  - defusedxml

インストール例（プロジェクトルートで）:
```bash
python -m pip install -e .       # パッケージの編集可能インストール（setup/pyproject がある想定）
python -m pip install duckdb defusedxml
```

（pyproject.toml / requirements.txt があればそちらで管理してください）

---

## 環境変数

主に次の環境変数を利用します（必須のものは README の例に従って .env に設定してください）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（Execution 系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（監視/通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルートの `.env` および `.env.local` を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順位）。
- テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境に設定してください。

例: .env (プロジェクトルート)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境と依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .
   python -m pip install duckdb defusedxml
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env`（必要な値を記載）を作成するか、OS 環境変数に設定します。

4. DuckDB スキーマ初期化
   - 初期スキーマを作成して DuckDB に接続する例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスを指定、":memory:" でインメモリ
   ```
   - 監査ログ専用 DB を使う場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的なユースケース）

- 日次 ETL を実行して株価・財務・カレンダーを取得する
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュース収集ジョブを実行する（RSS → raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- J-Quants から日足データを直接取得して保存する（テストや部分取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)}, saved={saved}")
```

- 研究用ファクター計算（例: momentum）
```python
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum
from datetime import date

conn = init_schema("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2024,2,2))
# factors は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

- ファクターの z-score 正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, columns=["mom_1m", "ma200_dev"])
```

- 品質チェックを手動で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 注意点 / 運用上の配慮

- J-Quants API の利用にはトークンが必要です。`JQUANTS_REFRESH_TOKEN` を .env に設定してください。
- jquants_client は内部でレート制御とリトライを行いますが、API 利用制限や契約条件はユーザ側で確認してください。
- DuckDB への DDL/INSERT は基本的に冪等に設計されていますが、外部から直接 DB を変更した場合や別バージョンの DuckDB を使うと互換性の問題が生じる可能性があります。
- 監査ログ（audit）テーブルは UTC タイムゾーンで統一します。init_audit_schema は接続に `SET TimeZone='UTC'` を実行します。
- 自動 .env 読み込みはプロジェクトルートを基準に行います。テスト時などに自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント + 保存ユーティリティ
      - news_collector.py            — RSS ニュース収集・保存
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — 統計ユーティリティ（z-score 等）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - quality.py                   — データ品質チェック
      - calendar_management.py       — 市場カレンダー更新・営業日ロジック
      - audit.py                     — 監査ログ初期化・DDL
      - features.py                  — 特徴量ユーティリティ公開
      - etl.py                       — ETLResult 再エクスポート
    - research/
      - __init__.py
      - feature_exploration.py       — 将来リターン計算 / IC / summary
      - factor_research.py           — momentum/volatility/value の計算
    - strategy/                       — 戦略層（雛形） ※実装は個別に追加
    - execution/                      — 発注/約定処理（雛形） ※実装は個別に追加
    - monitoring/                     — 監視・稼働状況管理（雛形）
- pyproject.toml / setup.cfg / README.md 等（プロジェクトルート）

---

## 貢献 / 開発

- コードスタイル・設計方針は既存ファイルのコメント（docstring）に準拠してください。
- テストや CI、型チェック（mypy）を導入することを推奨します。
- セキュリティ・運用上の注意点（API トークン管理、SSRF 対策、XML パースの安全化）はドキュメントに従ってください。

---

必要であれば README にサンプル .env.example、より詳しい ETL 実行スケジュール例（cron / Airflow / Prefect 連携案）、監視 / Slack 通知のサンプルコードを追加できます。どの内容を追加希望か教えてください。