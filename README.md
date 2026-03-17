# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や RSS を利用したデータ収集、DuckDB によるスキーマ定義・保存、ETL パイプライン、ニュース収集と品質チェック、マーケットカレンダー管理、監査ログの初期化など、アルゴリズム取引のデータ基盤に必要な機能群を提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）保存による Look-ahead 防止
  - DuckDB への冪等的保存（ON CONFLICT / DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分フェッチ + バックフィル）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合）を実行して報告

- ニュース収集（RSS）
  - RSS フィードから記事を取得し DuckDB に冪等保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 の先頭で記事 ID を生成
  - SSRF 対策（スキーム検査、プライベートアドレスブロック、リダイレクト検査）
  - defusedxml による XML 攻撃対策、受信サイズ制限（メモリ DoS 対策）

- マーケットカレンダー管理
  - JPX カレンダーを差分更新
  - 営業日判定・前後営業日の取得・期間内営業日リスト取得などのユーティリティ

- 監査ログ（Audit schema）
  - シグナル → 発注 → 約定 に至るトレーサビリティテーブル群の初期化
  - 発注リクエストの冪等キー、UTC タイムスタンプポリシー

- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義とインデックス
  - init_schema / init_audit_schema / init_audit_db などの初期化関数

---

## 前提条件

- Python 3.10 以上（typing の `|` 演算子等を使用しています）
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml

（その他は標準ライブラリの urllib 等を利用しています。追加で Slack 連携や DB を使う場合は対応クライアントをインストールしてください）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとして開発環境にインストールする場合:
```bash
git clone <repo>
cd <repo>
python -m pip install -e .
```
（pyproject.toml / setup.py がある場合は通常の方法でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／取得する
2. Python の仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. DuckDB ファイル保存先のディレクトリを作成（自動作成されるため省略可）
5. 環境変数を設定（.env を推奨）

環境変数は .env / .env.local / OS 環境変数から自動読み込みされます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の主要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用途の Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意/デフォルト値の変数:
- KABU_API_BASE_URL : kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...）（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡易例）

以下は基本的な操作のサンプルです。実行するには上で示した環境変数を設定し、duckdb と defusedxml をインストール済みであることを確認してください。

- DuckDB スキーマを初期化する
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 既存ならスキップ（冪等）
```

- 日次 ETL を実行する（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn)  # デフォルトは today を対象
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ（差分取得）
```python
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- ニュース収集の実行（RSS → raw_news）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知銘柄コードセット（銘柄抽出に使用）
known_codes = {"7203", "6758", "9984"}
# デフォルトソースを利用
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 監査ログ（Audit schema）の初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## ログと環境モード

- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかである必要があります。無効な値はエラーになります。
- LOG_LEVEL によってログ出力の閾値を制御します（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）。

---

## ディレクトリ構成（抜粋）

プロジェクトは src パッケージレイアウトになっています。主なファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                   : 環境変数 / .env 読み込み・設定
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         : RSS ニュース収集・保存・銘柄抽出
    - schema.py                 : DuckDB スキーマ定義・初期化
    - pipeline.py               : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    : マーケットカレンダー管理とユーティリティ
    - audit.py                  : 監査ログ用スキーマ（signal/events/order_requests/executions）
    - quality.py                : データ品質チェック
  - strategy/
    - __init__.py               : 戦略層の名前空間（実装はここに追加）
  - execution/
    - __init__.py               : 発注・約定層の名前空間（実装はここに追加）
  - monitoring/
    - __init__.py               : 監視関連（実装を追加）

- その他:
  - pyproject.toml / setup.cfg など（存在する場合、パッケージング情報）

---

## 開発時の注意点 / 設計方針（要点）

- DuckDB の INSERT は冪等性を意識して ON CONFLICT 句を多用しています（再実行可能な ETL を想定）。
- API 呼び出しにはレート制限とリトライ、401 時の自動リフレッシュを組み込んでいます。
- ニュース収集は SSRF 対策、受信サイズ制限、XML 安全パッケージの使用などセキュリティに配慮しています。
- 品質チェック（quality.run_all_checks）は Fail-Fast ではなく問題の全数検出 → 呼び出し元が対応を判断する方針です。
- すべてのタイムスタンプ（監査用等）は UTC を前提としています。

---

## 貢献・拡張

- strategy や execution パッケージにアルゴリズムやブローカ接続を実装して拡張してください。
- 新しい RSS ソースは news_collector.DEFAULT_RSS_SOURCES に追加可能です。
- ETL のスケジューリングは外部（cron / Airflow / 他のジョブランナー）で行い、pipeline.run_daily_etl を呼び出す運用を想定しています。

---

必要であれば、README に CLI 実行例、より詳細な .env.example、requirements.txt、ユニットテスト実行方法（pytest 等）を追加します。追加希望があれば教えてください。