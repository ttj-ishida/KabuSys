# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ群）。データ取得・ETL・品質チェック・監査ログなど、アルゴリズム取引の基盤となる機能を提供します。

主な想定用途:
- J-Quants API からの市場データ（株価/財務/カレンダー）取得と DuckDB への永続化
- RSS ニュース収集と記事→銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL パイプラインの実行（差分更新・バックフィル・先読みカレンダー）
- 発注・監査用スキーマ（監査ログ・オーダー追跡）の初期化（設計のみ含む）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（必要に応じて無効化可能）
  - 必須変数未設定時に明確なエラーを返す Settings API

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限 (120 req/min) 対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、401 のトークン自動リフレッシュ処理含む）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- RSS ニュース収集（kabusys.data.news_collector）
  - RSS 取得、XML の安全パース（defusedxml）
  - URL 正規化／トラッキングパラメータ除去、記事ID を SHA-256 の先頭 32 文字で生成
  - SSRF 対策（スキーム検証、プライベートIP拒否、redirect 前検査）
  - レスポンスサイズ制限 / gzip 解凍後の検査
  - DuckDB へ冪等保存（INSERT ... RETURNING）と銘柄紐付け（news_symbols）

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化ユーティリティ（init_schema / get_connection）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィル・先読みカレンダーを組み合わせた日次ETL（run_daily_etl）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - 品質チェック連携（kabusys.data.quality）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトのリストで返却（severity で判断可能）

- 監査ログ定義（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブル定義と初期化補助

---

## 前提・依存関係

- Python 3.10 以上（型注釈の構文で | None を使用）
- 必須ライブラリ（少なくとも以下をインストールしてください）
  - duckdb
  - defusedxml

（パッケージ化時に requirements を用意する想定です）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発中であれば）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config が提供）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 などを設定してから Python を起動してください。

必須の環境変数（ライブラリ内で Settings を参照する箇所で必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルト値あり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

例 `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

以下は基本的な利用例。Python REPL やスクリプトで実行します。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数から取得されます（未設定時は data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2. 日次ETL の実行（J-Quants から差分取得して保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトは今日を対象に実行
print(result.to_dict())
```

3. RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection

# known_codes はサイトで参照する有効な銘柄コードの集合（重複検出防止等）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4. 個別 API 利用例（J-Quants の id token 取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

id_token = get_id_token()
quotes = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
```

5. テスト向け: インメモリ DB を使う
```python
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
```

エラーハンドリング:
- run_daily_etl 等は内部でステップごとに例外を捕捉して処理を継続します。戻り値の ETLResult.errors / quality_issues を確認してください。

ログ:
- 環境変数 LOG_LEVEL でログレベルを制御できます。
- KABUSYS_ENV により実行モード（development / paper_trading / live）を切り替えます。

---

## ディレクトリ構成

以下は主要モジュールの構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (発注/実行に関する実装の置き場、空の __init__ を含む)
  - strategy/  (戦略関係の実装の置き場、空の __init__ を含む)
  - monitoring/ (監視用モジュールの置き場、空の __init__ を含む)
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマと初期化ユーティリティ
    - pipeline.py            — ETL パイプライン（差分更新/バックフィル/品質チェック）
    - audit.py               — 監査ログテーブル定義・初期化
    - quality.py             — データ品質チェック
  - その他:
    - package metadata (pyproject.toml などがある想定)

---

## 運用上の注意

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に行います。CI やテスト時に自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限（120 req/min）に準拠するよう内部で制御していますが、大量ページネーションや同時実行を行う場合は追加の配慮が必要です。
- RabbitMQ / 実際のブローカー連携・Slack 通知などは本コードベースの一部（環境変数設定やスキーマ）で想定されていますが、ブローカー API 向けの実装は別途実装が必要です。
- DuckDB に対する大量のバルク挿入はチャンク処理およびトランザクションで最適化していますが、運用環境では I/O やバックアップポリシーを検討してください。

---

## 貢献・拡張

- strategy / execution / monitoring ディレクトリに戦略・実行・監視機能を実装して拡張してください。
- 新しいデータソースや品質チェックを追加する場合は、既存の ETL パイプラインに統合してください。
- テスト: ネットワーク呼び出し部（_urlopen 等）は差し替えやモックを容易にする設計になっています。ユニットテストを追加してください。

---

以上。必要であれば README に実行例のより詳細な手順（systemd / cron / Airflow 連携例、CI 設定、.env.example ファイルテンプレートなど）を追加しますので、用途に合わせて教えてください。