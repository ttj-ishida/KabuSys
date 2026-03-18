# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ/バックエンドコンポーネント群）

このリポジトリは、J-Quants や kabuステーション 等の外部サービスから市場・財務・ニュース等のデータを取得し、
DuckDB に格納、品質チェック・ETL を実行し、戦略／発注／監査ログのための基盤機能を提供します。

---

## 主要な特徴（抜粋）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダー取得
  - レート制限 (120 req/min) に準拠する内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）、408/429/5xx をリトライ
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して再試行
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を取得して前処理（URL除去・空白正規化）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュ（先頭32文字）を記事IDにして冪等挿入
  - defusedxml を使った XML パース（XML Bomb 等の防御）
  - SSRF 対策（スキーム検証、リダイレクト先の内部IP検査）、レスポンスサイズ制限
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING）と銘柄紐付け

- DuckDB スキーマ定義 & 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義一式
  - インデックス定義、監査ログ用スキーマ（order_request_id の冪等制御等）
  - init_schema / init_audit_db による初期化

- ETL パイプライン
  - 差分更新（最終取得日から必要範囲を自動算出）
  - backfill による後出し修正吸収
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行し問題を返却
  - 日次 ETL run_daily_etl の一括実行

- 市場カレンダー管理
  - カレンダー差分更新ジョブ、営業日判定、前後営業日探索、範囲内営業日列挙
  - DB 未登録時は曜日ベースでフォールバック

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の階層で完全トレースを保持
  - UTC タイムスタンプ、削除しない前提の設計、各種制約とインデックス

---

## 必要な環境変数（主なもの）

このパッケージは環境変数から設定を読み込みます（.env / .env.local / OS 環境変数）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視DBなどに用いる SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定するとパッケージの自動 .env ロードを無効化

自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込みます。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
KABU_API_PASSWORD=あなたの_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（開発環境向け）

※このリポジトリの依存関係管理ファイル（pyproject.toml / requirements.txt）は別途存在する前提です。以下は一般的な手順例です。

1. Python のインストール（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージとして配布されている場合）pip install -e .
4. プロジェクトルートに .env を作成（上記の必須環境変数を設定）
5. DuckDB スキーマ初期化（例）:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

備考:
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- .env.local は .env を上書きする用途（ローカルの秘密情報）に使われます。

---

## 使い方（主要 API と実行例）

以下はライブラリ API を直接呼び出す例です。プロダクションジョブ・CLI は含まれていないため、用途に応じてラッパースクリプトを作成してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログ専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを一括実行）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使用する有効コード集合（例: {'7203','6758',...}）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)  # {source_name: saved_count}
```

- 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
```

- 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for issue in issues:
    print(issue)
```

- J-Quants からのデータ取得（下位 API）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系関数を使って DuckDB に保存できます。

---

## セキュリティ・品質に関する設計ノート

- J-Quants クライアントはレート制限とリトライを備え、401 を受けたらトークンをリフレッシュして再試行する設計。ページネーション時は id_token をモジュール内キャッシュで共有。
- news_collector は defusedxml を利用して XML 攻撃に備え、レスポンスの最大バイト数を厳しく制限（既定 10 MB）、gzip 解凍後も検査します。
- RSS のリダイレクトや最終 URL に対して SSRF 対策（スキーム検査・内部 IP 拒否）を行っています。
- DuckDB への挿入は基本的に冪等（ON CONFLICT）／トランザクションでまとめて実行。news のINSERTは RETURNING を使って実際に挿入された行を正確に把握します。
- すべての監査系 TIMESTAMP は UTC で保存する方針。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 & 保存）
    - news_collector.py      — RSS ニュース収集・前処理・保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — 市場カレンダー周りのユーティリティ
    - audit.py               — 監査ログ（トレーサビリティ）初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注・約定処理（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視系（未実装／拡張ポイント）

その他:
- pyproject.toml / setup.cfg 等（存在すればパッケージ管理）

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージはプレースホルダです。具体的な戦略やブローカー実装はここに追加します。
- ETL のユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境値をテスト内で注入してください。
- news_collector._urlopen はテストでモック差替え可能な設計になっています（外部ネットワークに依存する処理のテストが容易）。
- 実運用（live）では KABUSYS_ENV を "live" に設定し、はっきりと分離してください。

---

## 最後に

このライブラリは「データ取得→保存→品質チェック→戦略/発注へ渡す」までの強固な基盤を提供することを目的としています。実際の自動売買運用に組み込む際は、戦略層・リスク管理・発注レイヤーの十分な検証と安全策（回線障害・API 異常時のフェイルセーフ、実アカウントでの段階的ロールアウト）を行ってください。

ご不明点や README に追加してほしい使用例・運用手順があれば教えてください。