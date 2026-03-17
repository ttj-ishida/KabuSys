# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants など外部データソースから市場データ・財務データ・ニュースを収集し、DuckDB に蓄積、品質チェック、監査ログ、ETL パイプライン、カレンダー管理などを提供します。

主な設計方針として、冪等性（ON CONFLICT）、Look-ahead バイアス回避（fetched_at の記録）、API レート制限遵守、堅牢なエラーハンドリングを重視しています。

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動ロード（OS 環境変数 > .env.local > .env）
  - 主要な必須設定に対する検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）とリトライ（指数バックオフ、401 時自動トークン更新）対応
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理（URL 除去・正規化）、記事IDの冪等生成（正規化URL の SHA-256）
  - SSRF 対策、受信サイズ制限、XML 安全パーサ（defusedxml）適用
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 相当のテーブル定義
  - 初期化関数: init_schema / init_audit_db
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日の差分のみ取得、バックフィル対応）
  - 日次 ETL 実行エントリポイント run_daily_etl
  - 品質チェック連携（kabusys.data.quality）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合 等の検出（QualityIssue を返す）
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査テーブルと初期化

---

## 要件

- Python 3.10+
- 外部パッケージ
  - duckdb
  - defusedxml

（標準ライブラリの urllib / gzip / logging 等も使用）

インストール例:
```bash
python -m pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があればそれを利用
# python -m pip install -r requirements.txt
```

---

## 環境変数（主なもの）

このライブラリは環境変数から設定を読み込みます。必須のものは未設定時に ValueError を送出します。

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite パス（監視用デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト向け）

.env の自動読み込みについて
- 自動読み込みの探索はパッケージファイルの位置を起点にプロジェクトルート（.git または pyproject.toml を上位で探索）を特定して行います。
- 読み込み順: OS 環境変数 ＞ .env.local ＞ .env
- .env の文法は export KEY=val、クォート、コメント等を考慮した解析を行います。

---

## セットアップ手順（簡易）

1. Python 環境準備（3.10+）
2. 依存パッケージインストール:
   pip install duckdb defusedxml
3. 環境変数を設定（またはプロジェクトルートに .env を作成）
   - 例: .env に JQUANTS_REFRESH_TOKEN=... を記載
4. DuckDB スキーマ初期化
   - サンプルコード（Python）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
5. 監査ログ DB 初期化（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な API / ワークフロー）

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) カレンダー夜間更新ジョブを単独で実行
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

4) ニュース収集（RSS）を実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection, init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効銘柄コードの set（省略すると抽出スキップ）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規挿入件数}
```

5) J-Quants API を直接使う（例: 株価取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

6) 品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

7) 監査スキーマの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 重要な設計・運用上の注意

- J-Quants API のレート制限（120 req/min）をコード側で厳守していますが、運用で更なる制御が必要な場合は上位で制限してください。
- jquants_client は 401 を受けた場合に自動的にリフレッシュトークンから ID トークンを更新して 1 回だけ再試行します。
- ETL は差分更新を基本とし、backfill_days により直近数日を再取得して API 側の後出し修正を吸収します。
- DuckDB への保存は多くの箇所で ON CONFLICT（冪等）を利用しており、繰り返し実行してもデータ整合性を維持します。
- news_collector は SSRF 対策、XML Bomb 対策、レスポンスサイズ制限などセキュリティ考慮を組み込んでいます。外部 RSS の取り扱いに注意してください。
- 環境によっては .env の自動ロードを無効化したい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（この README は src/ 配下の現状ファイルに基づいています）

- src/
  - kabusys/
    - __init__.py
    - config.py                         -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py               -- J-Quants API クライアント（fetch/save）
      - news_collector.py               -- RSS ニュース収集・保存
      - schema.py                       -- DuckDB スキーマ定義・初期化
      - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py          -- マーケットカレンダー管理
      - audit.py                        -- 監査ログスキーマと初期化
      - quality.py                      -- データ品質チェック
    - strategy/
      - __init__.py                      -- 戦略モジュール（拡張場所）
    - execution/
      - __init__.py                      -- 発注 / 実行モジュール（拡張場所）
    - monitoring/
      - __init__.py                      -- 監視機能（拡張場所）

---

## 開発・拡張のヒント

- strategy/ や execution/、monitoring/ はプレースホルダとして用意されています。戦略ロジックやブローカー連携はここを実装してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして .env 自動読み込みをオフにすると環境を固定しやすくなります。
- jquants_client のリクエスト挙動は urllib を使った同期実装です。高負荷運用で非同期化や追加レート管理が必要な場合は改変を検討してください。
- DuckDB に対する SQL は多くがパラメータバインド（?）を使用しているため、SQL インジェクションリスクは低く設計されています。DDL などで動的 SQL を作る部分がある場合は注意してください。

---

README に不足している具体的な運用手順や CI/CD、デプロイの例、または戦略実装のテンプレートが必要であれば、用途（バックテスト用、リアルタイム約定用、Paper Trading）に合わせた追加ガイドを作成します。必要な内容を教えてください。