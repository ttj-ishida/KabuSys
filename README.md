# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（プロトタイプ）

このリポジトリは、J-Quants API から日本株データを取得して DuckDB に格納し、品質チェックや戦略・発注層へ繋ぐための基盤機能群を提供します。ETL、スキーマ定義、監査ログ、J-Quants クライアント等を含み、後段の戦略実装や発注実行コンポーネントと組み合わせて自動売買システムを構築できます。

主な設計方針：
- API レート制限とリトライ、トークン自動リフレッシュを備えた堅牢なデータ取得
- DuckDB を用いた3層（Raw / Processed / Feature）スキーマ
- 冪等な保存（ON CONFLICT DO UPDATE）
- 品質チェック（欠損・重複・スパイク・日付不整合）
- 発注から約定に至る監査（トレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須変数チェックと設定ラッパー（settings オブジェクト）
- data.jquants_client
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レートリミット（120 req/min）・リトライ（指数バックオフ）・401でのトークン自動リフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）
- data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
  - インデックス定義
- data.pipeline
  - 差分 ETL（市場カレンダー → 株価 → 財務）と品質チェックの統合実行
  - backfill（後出し修正吸収）やカレンダー先読み対応
  - ETL 実行結果を表す ETLResult
- data.quality
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue による問題報告（error / warning）
- data.audit
  - シグナル→発注要求→約定 の監査ログテーブル作成（トレーサビリティ保証）
- (戦略 / 実行 / モニタリング用のパッケージプレースホルダ)

---

## セットアップ

前提
- Python 3.10 以上（型注釈で PEP 604 の `|` を使用しているため）
- duckdb パッケージ（DuckDB Python）

推奨手順（Unix 系）:

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
```

もし他の依存が増えた場合は requirements.txt を用意して `pip install -r requirements.txt` を行ってください。

2. 環境変数 / .env の準備

必須の環境変数（少なくとも以下を設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等に使用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

プロジェクトルート配下に `.env` / `.env.local` を置くと、自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順位）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env`（保護された鍵なので Git に含めないでください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な API と実行例）

以下はライブラリをインポートして基本操作を行う例です。プロジェクトをパッケージとして使える状態であることを前提とします（`pip install -e .` あるいは PYTHONPATH に src を追加）。

1. DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
```

2. 監査ログテーブルを追加する（必要に応じて）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3. J-Quants の ID トークンを取得する（内部でリフレッシュトークンを使う）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を利用
```

4. 日次 ETL を実行する（デフォルトは今日）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult の内容を確認
```

5. ETL の個別実行（株価・財務・カレンダー）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

target = date.today()
fetched, saved = run_prices_etl(conn, target)
```

6. 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

ログ設定や詳細なエラー処理はアプリ側でロギングレベルやハンドラを設定して行ってください（settings.log_level を参照）。

---

## 実装上のポイント / 注意点

- J-Quants クライアント
  - レート制限は固定間隔スロットリングで 120 req/min を守ります。
  - リトライは指数バックオフ（最大 3 回）、HTTP 408/429/5xx を対象。
  - 401 が返った場合はリフレッシュトークンで自動的に ID トークンを更新して 1 回だけ再試行します。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead Bias を防止します。

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の多層設計。
  - ON CONFLICT DO UPDATE を利用した冪等保存。
  - 監査ログテーブルは UTC タイムゾーンでの運用を想定（init_audit_schema は SET TimeZone='UTC' を実行）。

- 環境変数の読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を上位ディレクトリから探索して .env を自動で読み込みます。CIやテストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- データ品質
  - 欠損（OHLC）、スパイク（前日比 50% 既定）、重複、非営業日/未来日などを検査します。
  - 品質チェックは全件収集方式（Fail-Fast ではない）で、呼び出し元が致命度に応じて対応を決定します。

---

## ディレクトリ構成

リポジトリ内の主要ファイルと構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       （環境設定読み込み・settings）
  - data/
    - __init__.py
    - jquants_client.py              （J-Quants API クライアント）
    - schema.py                      （DuckDB スキーマ定義 / init_schema）
    - pipeline.py                    （ETL パイプライン）
    - quality.py                     （データ品質チェック）
    - audit.py                       （監査ログテーブル）
    - audit.py
  - strategy/
    - __init__.py                    （戦略層プレースホルダ）
  - execution/
    - __init__.py                    （発注実行プレースホルダ）
  - monitoring/
    - __init__.py                    （監視用プレースホルダ）

（注）README に記載のファイルはこのリポジトリに含まれる主要なモジュールに基づきます。上記以外にユーティリティや CLI を追加することが想定されます。

---

## よくある質問

- Q: .env の読み込みタイミングはいつですか？
  - A: kabusys.config モジュールのインポート時に、プロジェクトルートを探して .env / .env.local を読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。

- Q: DuckDB の初期化は何を作成しますか？
  - A: raw_prices / raw_financials / market_calendar / features / signals / orders / trades / positions 等、Raw→Processed→Feature→Execution にまたがるテーブル群とインデックスを作成します。既に存在する場合はスキップ（冪等）。

- Q: J-Quants の API レート制限を気にする必要はありますか？
  - A: 内部で 120 req/min のレート制御とリトライを行っているため、通常は気にする必要はありません。ただし外部ループなどで短時間に大量リクエストを投げる場合は注意してください。

---

## 今後の拡張案

- 発注実行（kabu ステーション）との統合コード（order フロー・再試行・約定取り込み）
- Slack / メトリクスを使った監視アラートの実装
- CLI / Scheduler（cron 代替）での定期実行スクリプト
- 戦略（strategy 層）とポートフォリオ最適化モジュール

---

フィードバックや不具合報告、機能追加の提案は issue を立ててください。