# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS などからデータを収集し、DuckDB に保存、ETL・品質チェック・監査ログなどの基盤機能を提供します。

主な設計方針は以下です。
- API レート制御・リトライ・トークン自動更新を備えた堅牢なデータ取得
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- Look-ahead bias の回避（fetched_at / UTC タイムスタンプ）
- RSS ニュース収集の SSRF・XML Bomb 対策、記事正規化と銘柄紐付け
- データ品質チェックと監査（signal → order → execution のトレース）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
    - レートリミット（120 req/min）、指数バックオフ、401 自動リフレッシュ対応
  - RSS ニュース収集（トラッキングパラメータ除去、SSRF対策、gzip制限）
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマ（signal / order_request / executions）

- ETL / 管理
  - 差分 ETL（価格、財務、カレンダー）
  - 日次 ETL エントリポイント（品質チェック付き）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- 補助
  - 設定管理（.env 自動読み込み、必要環境変数チェック）
  - ログ連携や運用向けに Slack 等のトークンを管理可能（設定のみ）

---

## 前提条件

- Python >= 3.10（typing の `X | Y` 構文を使用）
- 必要なライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging 等）

インストールはプロジェクトの pyproject.toml / setup を想定しています。開発中は editable インストールが便利です。

例:
```bash
python -m pip install -e .
python -m pip install duckdb defusedxml
```

---

## 環境変数（主要）

.env ファイルまたは OS 環境変数から読み込みます。プロジェクトルート（.git または pyproject.toml を含むディレクトリ）から `.env` → `.env.local` の順で自動ロードされます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例（.env）:
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン・移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存関係をインストール
   ```bash
   python -m pip install -e .
   python -m pip install duckdb defusedxml
   ```

4. 環境変数を準備（.env または環境へ設定）
   - 上記の必須変数を設定してください。

5. DuckDB スキーマを初期化
   - 例: デフォルトパス（settings.duckdb_path）に初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（主な API / コマンド例）

以下は Python API を使った基本的な例です。

- DuckDB を初期化（in-memory の例）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- 日次 ETL を実行（デフォルト: 今日）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

- 株価のみ差分 ETL 実行（特定日を指定）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2025,1,10))
```

- 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

- ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {'7203','6758',...}）
results = run_news_collection(conn, sources=None, known_codes=known_codes)
```

- J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 監査スキーマの初期化（既存 conn に追記）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)     # Path オブジェクト
print(settings.is_live)         # bool
```

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効化するには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト時に環境の影響を排除したい場合に使用します。

- jquants_client のテストではネットワーク呼び出しやレート制御をモックしてください。
- news_collector の _urlopen を差し替えることで外部 HTTP をモックできます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得/保存）
    - news_collector.py             -- RSS ニュース取得・正規化・保存（SSRF/圧縮対策）
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（日次 ETL 等）
    - calendar_management.py        -- 市場カレンダー管理（営業日判定等）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログテーブル（signal/order_request/executions）
  - strategy/
    - __init__.py                   -- 戦略用パッケージ（実装場所）
  - execution/
    - __init__.py                   -- 発注/約定/ブローカ連携（実装場所）
  - monitoring/
    - __init__.py                   -- 監視・アラート関連（実装場所）

簡易ツリー:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  ├─ calendar_management.py
│  ├─ quality.py
│  └─ audit.py
├─ strategy/
│  └─ __init__.py
├─ execution/
│  └─ __init__.py
└─ monitoring/
   └─ __init__.py
```

---

## 参考・注意点

- すべてのタイムスタンプは UTC を使用する方針（特に監査ログ）。
- DuckDB の初期化は一度行えば既存テーブルは上書きされず冪等です。
- J-Quants の API 制限・429/Retry-After、401 などのハンドリングを組み込んでいますが、実運用ではさらに監視や再試行方針を検討してください。
- news_collector は外部の RSS をパースするため、defusedxml を利用して XML に対する安全対策をしています。

---

必要であれば、README にコマンドライン実行例や CI 用の簡易ジョブ定義（systemd / cron / GitHub Actions）のテンプレートも追加します。どのような利用シナリオ（例えばローカル運用・クラウド定期実行・Docker化）が主になりますか？それに合わせた追加ドキュメントを作成します。