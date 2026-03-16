# KabuSys

日本株向けの自動売買・データプラットフォームの骨組みを提供するライブラリです。  
J-Quants と kabuステーション（証券API）を中心に、データ取得（ETL）、データ品質チェック、DuckDB スキーマ（Raw/Processed/Feature/Execution）、および監査ログを提供します。

バージョン: 0.1.0

---

## 主な目的 / 概要

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に蓄積する ETL パイプラインを提供します。
- データ品質チェック（欠損、スパイク、重複、日付整合性）を行い、問題を検出します。
- Execution / Audit 用のスキーマを備え、シグナル→発注→約定までの監査（トレーサビリティ）をサポートします。
- レート制限・リトライ・トークン自動リフレッシュ等の堅牢な API クライアント実装を含みます。

---

## 機能一覧

- data.jquants_client
  - get_id_token(refresh_token=None): J-Quants のリフレッシュトークンから ID トークンを取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応で J-Quants から取得
  - save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - レート制限（120 req/min）・リトライ（指数バックオフ、最大3回）・401 時のトークン自動リフレッシュ対応

- data.schema
  - init_schema(db_path)：Raw / Processed / Feature / Execution レイヤーのテーブルとインデックスを作成して DuckDB 接続を返す
  - get_connection(db_path)：既存 DB への接続取得

- data.audit
  - init_audit_schema(conn)：監査ログ用テーブルを既存接続へ追加
  - init_audit_db(db_path)：監査ログ専用 DB を初期化して接続を返す

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl：差分取得ロジック（バックフィル対応）で ETL を実行
  - run_daily_etl：カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック（オプション）を順次実行して ETLResult を返す

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks：すべてのチェックを実行し QualityIssue のリストを返す

- config
  - Settings クラス経由で環境変数を取得（必須・デフォルト値、バリデーション）
  - 自動 .env ロード機能（プロジェクトルートを .git / pyproject.toml で検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントの union `|` を使用）
- duckdb（DuckDB Python パッケージ）
- ネットワークアクセス（J-Quants API）
- 環境変数に API トークン等の設定が必要

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発用にパッケージ化されていれば: pip install -e .
```

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存を記載してください）

---

## 環境変数 / 設定項目

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意（デフォルトあり／検証あり）:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用途の SQLite パス。デフォルト: data/monitoring.db

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env/.env.local を読み込む機能を無効化します。

自動ロードの挙動:
- プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探して決定します。
- 読み込み優先順位: OS環境変数 > .env.local > .env
- .env のパースは一般的な export/クォート/コメントのケースに対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存をインストール
   - python3 -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb
   - （その他必要なライブラリをインストール）
3. プロジェクトルートに .env を作成（.env.example を参照）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     ```
4. DuckDB スキーマを初期化
   - Python スクリプトまたは REPL から init_schema を呼ぶ（例は次節）

---

## 使い方（基本的な例）

DuckDB スキーマ初期化と日次 ETL を行う簡単なスクリプト例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく
conn = init_schema(settings.duckdb_path)

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

監査ログテーブルの追加（既存接続への追加）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

J-Quants の個別取得 + 保存の例:

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))

# 例: 特定銘柄の株価を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

品質チェックの実行例:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意点:
- run_daily_etl は市場カレンダー取得 → 営業日調整 → 株価・財務データ取得 → 品質チェック の順で実行します。各ステップは独立してエラーハンドリングされ、問題があっても他ステップは継続します（結果は ETLResult に格納されます）。
- J-Quants API のレート制限や HTTP エラー時の挙動（リトライ、指数バックオフ、401 の自動トークン更新）を内部で扱います。

---

## 推奨ワークフロー例

- 日次バッチ
  - CI / Cron で次を実行:
    1. init_schema（初回のみ）
    2. run_daily_etl（取得 & 保存 & 品質チェック）
    3. 品質問題が重大（error）ならアラート（Slack 等）
- リアルタイム発注ワークフロー
  - 戦略層でシグナル生成 → audit.order_requests に挿入 → 発注モジュールで kabuAPI に送信 → executions に保存
  - すべての ID は UUID ベースで連鎖させトレーサビリティを保持

---

## ディレクトリ構成

概略（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - schema.py              # DuckDB スキーマ定義 / init_schema
      - pipeline.py            # ETL パイプライン（差分更新・バックフィル）
      - audit.py               # 監査ログ（signal/order_request/executions）
      - quality.py             # データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py            # 戦略用モジュール（拡張ポイント）
    - execution/
      - __init__.py            # 発注実行（拡張ポイント）
    - monitoring/
      - __init__.py            # 監視用モジュール（拡張ポイント）

---

## 注意事項 / 実装上のポイント

- Python の型注釈で 3.10 の構文（X | None）を使っているため Python 3.10 以上を推奨します。
- .env 自動ロードはプロジェクトルートを .git / pyproject.toml で検出します。配布後やテスト環境での挙動に注意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD で抑制可能）。
- DuckDB に対する INSERT は冪等（ON CONFLICT DO UPDATE）で設計されていますが、ETL の差分ロジック・バックフィル設定は適切に運用してください。
- 品質チェックは Fail-Fast とせず問題をすべて収集します。呼び出し側でどの程度の問題で処理を止めるかを判断してください。

---

## 今後の拡張ポイント（参考）

- kabuステーションとの通信・注文送信モジュールの実装（execution）
- 戦略モジュール（strategy）にプラグイン方式の戦略実装
- モニタリング / アラート（Slack 連携など）
- テストカバレッジ、CI パイプライン整備、ロギング/メトリクス強化

---

問題や改善提案があればお知らせください。README に追加したいコマンド例や設定例があれば反映します。