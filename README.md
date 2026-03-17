# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなど、戦略や発注層に必要な基盤機能を提供します。

## 主要機能
- J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - API レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大3回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- RSS ニュース収集器
  - RSS から記事を取得して前処理（URL除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml による XML インジェクション対策、SSRF 対策、受信サイズ上限
  - DuckDB へトランザクション単位で保存（INSERT ... RETURNING）し、銘柄紐付けをサポート
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）＋バックフィル（デフォルト 3 日）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日探索、夜間更新ジョブ）
- 監査ログ（signal / order_request / executions）スキーマ
  - 発注フローのトレーサビリティを UUID 連鎖で保証
- データ品質チェックモジュール
  - 欠損・スパイク・重複・日付不整合の検出と報告

---

## セットアップ手順

前提
- Python 3.9+（コードは typing | 型ヒントを利用）
- DuckDB（Python パッケージとして利用）
- defusedxml（RSS XML パースの安全化）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限の依存例:
     ```bash
     pip install duckdb defusedxml
     ```
   - パッケージとして開発インストールできる場合:
     ```bash
     pip install -e .
     ```
   （プロジェクトに requirements.txt や pyproject.toml があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` から自動読み込みされます（デフォルト）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABU_API_BASE_URL — kabuapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（コード例）

以下は最小限の初期化／実行例です。実運用ではログ・例外処理やスケジューラ（cron / Airflow 等）で定期実行してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイルを指定して初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマの追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3) 日次 ETL 実行（市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 引数省略で今日を対象に実行
print(result.to_dict())
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に使う有効コードのセット（渡さない場合は銘柄紐付けをスキップ）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

5) カレンダー夜間更新ジョブ（先読み・バックフィルを行う）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved", saved)
```

6) J-Quants API を直接呼ぶ（トークン取得など）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings の refresh token を使う
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,12,31))
```

7) 設定値の取得
```python
from kabusys.config import settings

print(settings.env, settings.jquants_refresh_token)
```

---

## ディレクトリ構成（主要ファイル）
以下はリポジトリ内の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動ロード・検証）
  - data/
    - __init__.py
    - schema.py              # DuckDB スキーマ定義・初期化
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py # マーケットカレンダー管理・ユーティリティ
    - audit.py               # 監査ログスキーマ（signal/order/execution）
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略関連の名前空間（実戦略はここに実装）
  - execution/
    - __init__.py            # 発注・実行管理の名前空間（ブリッジ実装等）
  - monitoring/
    - __init__.py            # 監視関連（未実装ファイル群の入り口）

（実装済みの関数・クラスは上記ファイル群にあります。個別の詳細は各モジュールの docstring を参照してください。）

---

## 設計上のポイント / 注意点
- 環境変数の自動読み込み
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を順に読み込みます。OS 環境変数は上書きされません（.env.local は override=True だが protected により OS 環境を保護）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- J-Quants クライアント
  - レート制限、リトライ、トークン自動リフレッシュ（401 に対して1回）の処理が組み込まれています。
  - 複数ページのページネーションに対応し、ページ間で ID トークンをキャッシュします。
- News Collector
  - defusedxml を使用して XML 攻撃を防止します。リダイレクトやホスト解決時にプライベートアドレス（SSRF）のアクセスを拒否します。
  - レスポンスサイズは上限（デフォルト 10 MB）で保護されています。
- DuckDB の初期化
  - init_schema() は冪等で何度呼んでも安全です。監査ログは別途 init_audit_schema() で追加できます。
- 品質チェック
  - check は Fail-Fast ではなく、すべてのチェックを実行して問題の一覧（QualityIssue）として返します。呼び出し側で重大度に応じたアクションを取ってください。

---

## よくある操作例 / トラブルシューティング
- .env が読み込まれない
  - import 時にプロジェクトルートが見つからないと自動ロードはスキップされます。環境変数を手動で export するか、プロジェクトルートに .env ファイルを置いてください。
- J-Quants の認証エラー（401）
  - _get_id_token_ により自動でリフレッシュを試みますが、refresh token が無効な場合は設定値（JQUANTS_REFRESH_TOKEN）を確認してください。
- DuckDB 接続エラー
  - 指定したパスの親ディレクトリに書き込み権限があるか確認してください。

---

## さらに進めること（運用上の提案）
- ETL の定期実行は cron / systemd timer / Airflow 等でスケジューリングしてください。
- run_daily_etl の戻り値を Slack などに通知して運用監視を行うと早期発見に有効です。
- 発注・ブローカー連携や戦略は strategy/, execution/ に適切なインターフェースを実装して統合してください。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト専用の環境変数注入を行うと安全です。

---

必要であれば、README 内に具体的な requirements.txt、CLI 実行例、あるいはデプロイ手順（systemd / Docker / k8s）向けのセクションも作成できます。どの追加情報が欲しいか教えてください。