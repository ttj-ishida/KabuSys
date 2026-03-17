# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
J-Quants などから市場データを取得して DuckDB に格納する ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ロギングなど、トレーディングシステムで必要となるデータ基盤・運用機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスを防止

- ETL パイプライン
  - 差分更新（最終取得日からの差分+バックフィル）
  - 市場カレンダー先読み
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行

- ニュース収集（RSS）
  - RSS フィードから記事を取得、前処理、DuckDB に冪等保存
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成
  - SSRF 対策、gzip サイズ制限、XML パースの安全化（defusedxml）

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ / 営業日判定ユーティリティ（次/前営業日、期間内営業日取得など）
  - DB に未登録時は曜日（土日）ベースでフォールバック

- データ品質チェック
  - 欠損、異常スパイク、主キー重複、日付不整合を SQL ベースで検出
  - QualityIssue オブジェクトとして問題一覧を返却

- DuckDB スキーマ管理 & 監査ログ
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査用テーブル（シグナル、発注要求、約定）を別途初期化可能（トレーサビリティ保持）

---

## 必要条件

- Python 3.10 以上（コードにおける型ヒント記法に依存）
- 必須 Python パッケージ:
  - duckdb
  - defusedxml

（その他は標準ライブラリの urllib 等を使用）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable インストールする場合:
pip install -e .
```

---

## セットアップ手順

1. ソースをクローン / ダウンロード
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数を設定
   - .env / .env.local をプロジェクトルートに置くと自動ロードされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings による検証）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知用（必須とされているが、使わない場面ではダミー可）
- SLACK_CHANNEL_ID : Slack チャネル ID

任意 / デフォルト:
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : environment ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",... ; デフォルト: INFO)

例 .env（プロジェクトルート）:
```env
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python REPL / スクリプトから呼ぶ代表的な API の例です。

- DuckDB スキーマを初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

- 監査ログ用スキーマを初期化（既存接続に追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- J-Quants の ID トークンを取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

- 日次 ETL を実行（株価・財務・カレンダー取得＋品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 戻り値は ETLResult
print(result.to_dict())
```

- ニュース収集ジョブを実行（既定 RSS ソースから収集）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
# conn は init_schema などで得た DuckDB 接続
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コード集合（任意）
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- カレンダー差分更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved", saved)
```

注意:
- J-Quants API 呼び出しは RateLimiter による制御とリトライを行います。
- ETL / news collection は冪等性を意識して設計されています（ON CONFLICT / DO UPDATE / DO NOTHING を使用）。

---

## ディレクトリ構成（主要ファイル）

大まかなパッケージ構成:
```
src/kabusys/
├─ __init__.py
├─ config.py                      # 環境変数 / 設定管理
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py           # J-Quants API クライアント + DuckDB 保存
│  ├─ news_collector.py           # RSS ニュース収集・保存ロジック
│  ├─ schema.py                   # DuckDB スキーマ定義・初期化
│  ├─ pipeline.py                 # ETL パイプライン（run_daily_etl 等）
│  ├─ calendar_management.py      # カレンダー更新・営業日ユーティリティ
│  ├─ audit.py                    # 監査ログ（signal / order / execution）
│  └─ quality.py                  # データ品質チェック
├─ strategy/
│  └─ __init__.py                 # 戦略層（骨組み）
├─ execution/
│  └─ __init__.py                 # 発注・実行層（骨組み）
└─ monitoring/
   └─ __init__.py                 # 監視関連（骨組み）
```

主に data モジュールがデータ基盤機能を担います。strategy / execution / monitoring は今後の拡張ポイントを想定した空モジュールです。

---

## 実装上の留意点 / 補足

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に行われます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- ニュース収集では SSRF 対策（リダイレクト先検査、プライベートIP拒否）、gzip/レスポンスサイズ制限、defusedxml による XML 安全化などを実装しています。
- DuckDB スキーマは冪等に作成されます。既存テーブルは上書きされません。
- 監査ログ（audit）ではトランザクション設定に注意してください（DuckDB のトランザクション取り扱いに依存）。

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは拡張用の骨組みが用意されています。戦略ロジック、ポートフォリオ管理、実際のブローカー接続はここに実装してください。
- テストしやすさのため、jquants_client._urlopen や news_collector._urlopen 等はモック可能な設計になっています。
- ETL の id_token 注入や各種パラメータ（backfill_days, lookahead_days, spike_threshold）は関数引数でオーバーライドできます。

---

問題・バグ報告、機能要求はソース管理システム上の Issue に記載してください。README の補足やサンプルスクリプトが必要であれば作成します。