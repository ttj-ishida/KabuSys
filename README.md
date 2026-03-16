# KabuSys

日本株向け自動売買基盤のコアライブラリ（データ収集・ETL・品質管理・監査ログ基盤）

このリポジトリは、J-Quants API などから市場データを取得して DuckDB に永続化し、
戦略・実行レイヤーのためのデータ基盤と監査ログを提供するコンポーネント群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムにおけるデータ基盤・ETL・監査ログの骨格を提供します。
主な目的は以下です。

- J-Quants API からの株価（日足）、財務データ、JPX マーケットカレンダーの取得
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）と実行・監査テーブルの定義・初期化
- 差分更新・バックフィル・品質チェック（欠損、重複、スパイク、日付不整合）の自動化
- 発注〜約定に関する監査ログ（order_request_id 等の冪等キーを含む）を保持

設計上の特徴：
- API レート制限遵守（J-Quants: 120 req/min）とリトライ、トークン自動リフレッシュ
- ETL の冪等性（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast せず問題を収集して呼び出し元が判断可能にする
- 監査ログは時刻を UTC で保存し、トレーサビリティを重視

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - rate limiting（固定間隔）・リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ
  - DuckDB への保存用ユーティリティ save_daily_quotes / save_financial_statements / save_market_calendar（冪等）

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で DB 初期化（DDL + インデックス作成）

- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema(conn) / init_audit_db(db_path)

- data/pipeline.py
  - 日次 ETL の実装（run_daily_etl）
  - 差分取得、バックフィル、カレンダー先読み、品質チェック（quality モジュール）を統合

- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック
  - QualityIssue データクラスで問題を集約

- config.py
  - .env ファイルや環境変数の読み込み／管理
  - 自動 .env ロード（プロジェクトルートの検知）と保護された OS 環境変数
  - 必要環境変数の取得 API（settings）

---

## セットアップ手順（ローカル開発 / 実行用）

前提
- Python 3.10+ を推奨（PEP 604 の型記法 (A | B) を使用）
- DuckDB を利用するため `duckdb` パッケージが必要

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存ライブラリのインストール
   - 本リポジトリでは明示的な requirements.txt は含まれていませんが、最低限以下を入れてください:
     pip install duckdb

   - 実運用ではロギングや Slack 通知等のライブラリが必要になる場合があります。

4. 環境変数の設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限設定が必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から ETL を実行する最小例です。

1) DuckDB スキーマ初期化と日次 ETL 実行例

```python
from datetime import date
from kabusys.data import schema, pipeline

# DB を初期化（ファイルがなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると本日）
result = pipeline.run_daily_etl(conn)

# 結果を辞書化して表示
print(result.to_dict())
```

2) 監査ログスキーマの初期化

```python
from kabusys.data import schema, audit

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査用テーブルを追加
```

3) J-Quants クライアントを直接利用する例

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb

conn = schema.init_schema("data/kabusys.duckdb")

# トークンは settings により自動で環境変数から取得されます
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

パラメータのポイント：
- pipeline.run_daily_etl(..., backfill_days=3, calendar_lookahead_days=90, run_quality_checks=True)
  - backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3 日）
  - calendar_lookahead_days: カレンダーを先読みする日数（デフォルト 90 日）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - execution/                # 実行（発注）関連モジュール（スケルトン）
    - __init__.py
  - strategy/                 # 戦略関連（スケルトン）
    - __init__.py
  - monitoring/               # モニタリング関連（スケルトン）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント＋DuckDB 保存ユーティリティ
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分更新 + 品質チェック）
    - audit.py                # 監査ログスキーマ初期化
    - quality.py              # データ品質チェック

パッケージルート:
- pyproject.toml, setup.cfg 等がある場合は _find_project_root() で検出し .env 自動読み込みに利用します。

---

## 設計上の注意点・運用メモ

- API レート制限: jquants_client は 120 req/min を固定間隔スロットリングで守るよう実装されています。大量の銘柄を一括取得する際は時間に注意してください。
- 再現性・トレーサビリティ: データ取得時刻（fetched_at）は UTC タイムスタンプで保存されます。Look-ahead bias を防ぐために「いつシステムがそのデータを知り得たか」を追跡できます。
- 品質チェック: run_daily_etl は品質問題を検出しても ETL を継続し、QualityIssue のリストを返します。呼び出し元で警告/停止判断を行ってください。
- 環境変数自動読み込み: 開発時は .env/.env.local に機密情報を書き込むことが多いため、`.env.local` は `.gitignore` に入れて管理することを推奨します。
- KABUSYS_ENV の値: "development", "paper_trading", "live" のいずれかを指定して挙動（実行フラグ等）を分けられます。間違った値を指定するとエラーになります。

---

## 今後の拡張ポイント（参考）

- strategy レイヤの実装（シグナル生成・リスク管理）
- execution レイヤの broker 接続（kabuステーションや証券会社 API 実装）
- Slack 通知・監視ダッシュボードとの連携（monitoring モジュール）
- 単体テスト・統合テストと CI の追加
- requirements.txt / packaging（pip install 可能にする）

---

作業や導入で不明点があれば、どの部分（ETL 実行、DB 初期化、環境変数、J-Quants の使い方等）について詳しく知りたいか教えてください。さらに具体的な使用例やサンプルスクリプトを用意します。