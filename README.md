# KabuSys

日本株向けの自動売買（データ収集・ETL・監査・監視）ライブラリです。J-Quants や RSS を利用して市場データ／ニュースを取得し、DuckDB に格納・品質検査を行ったうえで、戦略／実行／監視レイヤに引き渡すための基盤機能を提供します。

主な設計方針：
- 冪等性（DB への保存は ON CONFLICT で重複を排除）
- API レート制御とリトライ（J-Quants クライアント）
- Look-ahead bias 回避のため取得時刻を記録（UTC）
- RSS 収集での SSRF・XML 攻撃・メモリ DoS 対策
- DuckDB を中心とした軽量・高速なローカルデータレイク

---

## 機能一覧

- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制限（120 req/min）とリトライ（指数バックオフ）
  - 401 時の自動トークンリフレッシュ

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化 API（init_schema / init_audit_db）

- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック（差分更新・バックフィル対応）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl

- ニュース収集（RSS）
  - RSS フィードの取得・前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）
  - defusedxml による XML パース、SSRF リダイレクト検査、サイズ上限ガード
  - raw_news / news_symbols への冪等保存

- データ品質チェック
  - 欠損データ検出、主キー重複検出、前日比スパイク検出、日付整合性チェック
  - QualityIssue オブジェクトリストで結果返却

- カレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト取得
  - calendar_update_job による夜間差分更新

- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査向けテーブル
  - UTC タイムゾーン固定、発注冪等キー対応

---

## 前提条件

- Python 3.10+
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml

例（最低限インストール）:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとして扱う場合は、setup/pyproject に従って依存をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存インストール
   ```bash
   python -m pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject があればそちらを使用）

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` / OS 環境変数から設定を読み込みます。
   - 自動読み込みをテスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャネル ID

オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1）
- KABUSYS_LOG_LEVEL / LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_API_BASE_URL / KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）

例 .env（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ワークフロー）

以下は Python から直接実行する例です。スクリプト化して cron / Airflow / CI 等で定期実行する想定です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL（カレンダー、株価、財務、品質チェック）
```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続
result = pipeline.run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())  # ETLResult を辞書化して確認
```

3) ニュース収集（RSS）と保存
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルト RSS ソースを使用
res = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存件数}
```

4) カレンダー夜間更新ジョブ（calendar_update_job）
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

5) 監査スキーマの初期化（audit テーブル）
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
# または専用 DB を作る:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

ログ設定例（簡易）:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

注意:
- J-Quants API での大量リクエストはレート制限（120 req/min）を守ってください。jquants_client には RateLimiter とリトライ処理が入っています。
- テスト時などで .env の自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動読込）
  - data/
    - __init__.py
    - schema.py                   — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py           — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - news_collector.py           — RSS ニュース収集と保存（SSRF・XML 保護、idempotent 保存）
    - calendar_management.py      — マーケットカレンダー管理（営業日判定、update_job）
    - quality.py                  — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                    — 監査ログ用テーブルの初期化
    - pipeline.py                 — ETL ワークフロー（差分更新など）
  - strategy/
    - __init__.py                 — 戦略レイヤ（拡張ポイント）
  - execution/
    - __init__.py                 — 発注/実行レイヤ（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視機能（拡張ポイント）

その他:
- .env / .env.local / .env.example（プロジェクトルートに置く想定）
- data/（デフォルトの DB 保存先）

---

## 設計上の注意点 / ベストプラクティス

- DuckDB はトランザクションをサポートします。news_collector などはトランザクションでまとめて挿入／ロールバックを行います。
- jquants_client は 401 時に自動トークンリフレッシュを試みますが、無限再帰にならないよう allow_refresh フラグを使用しています。
- news_collector は外部入力（RSS）の扱いに慎重で、XML Bomb / Gzip Bomb / SSRF を考慮した実装になっています。
- ETL は差分更新（最終取得日ベース）＋バックフィルを行い、API 側の後出し修正に耐性を持たせる設計です。
- 本パッケージは基盤レイヤを提供します。実際の運用では「戦略」「発注ブリッジ（kabu ステーション連携）」「監視・アラート」の実装を追加してください。

---

以上が README の要約です。必要であれば、README に含めるサンプルスクリプト（定期実行用 wrapper、Docker / systemd ユニット例、CI 用ワークフロー）や、より詳細な .env.example の雛形、運用時注意事項（バックアップ、DB ローテーション、機密情報管理）を追加で作成できます。どれを追加しますか？