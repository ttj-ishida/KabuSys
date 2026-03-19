# KabuSys

KabuSys は日本株のデータ収集・特徴量生成・シグナル生成・発注監査を想定した自動売買フレームワークです。本リポジトリは以下のレイヤ（モジュール群）を備え、研究 → データパイプライン → 戦略 → 発注監査までのワークフローをサポートします。

主な設計方針
- ルックアヘッドバイアスの回避（計算・シグナルは target_date 時点のデータのみを使用）
- DuckDB を用いたローカル DB（冪等保存・トランザクション）
- 明示的な品質チェック・ロギング・リトライやレート制御
- 本番の発注 API への直接依存を避けた層分離（strategy は execution に依存しない）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定ロード（.env / .env.local 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ニュース収集（RSS → 前処理 → raw_news に冪等保存、銘柄抽出）
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリ
- 特徴量エンジニアリング（研究で算出した raw factor を正規化・統合して features テーブルへ保存）
- シグナル生成（features + ai_scores を統合して final_score を算出、BUY/SELL を生成）
- 発注監査（signal → order_request → execution のトレーサビリティ、監査テーブル）
- マーケットカレンダー管理（営業日判定・next/prev/trading days 等）

---

## 要件

- Python 3.10 以上（PEP 604 の型表記等を使用）
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml

インストールコマンド例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# プロジェクトを editable インストールできる場合:
# pip install -e .
```

（プロジェクトに pyproject.toml / setup.py がある想定なら pip install -e . を推奨します。）

---

## 環境変数

以下の環境変数を設定する必要があります（.env/.env.local から自動読み込みされます）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注を行う場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネルの ID

任意（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効にする場合に `1` を設定

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードの挙動:
- プロジェクトルートは __file__ の親階層から `.git` または `pyproject.toml` を探索して特定されます。
- 自動ロードは OS 環境変数 > .env.local > .env の優先順位で行われます。
- テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要ライブラリのインストール
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - リポジトリルートに `.env` または `.env.local` を作成し、上記の必須項目を設定します。
   - 例: `.env` を作る（.env.example を参考に作成する想定）

4. DuckDB スキーマ初期化
   ```python
   # Python REPL またはスクリプトで
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - ":memory:" を与えるとインメモリ DB が作成されます。

---

## 使い方（代表的な操作例）

下記は最小限の操作例です。プロダクション用途ではログ・エラーハンドリング・スケジューリング（cron / Airflow 等）を用いて運用してください。

1. DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た接続
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3. 研究用ファクター計算（単独で呼ぶ場合）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
records_mom = calc_momentum(conn, date(2025, 1, 15))
records_vol = calc_volatility(conn, date(2025, 1, 15))
records_val = calc_value(conn, date(2025, 1, 15))
```

4. 特徴量構築（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {count}")
```

5. シグナル生成（features / ai_scores / positions を参照して signals テーブルへ）
```python
from datetime import date
from kabusys.strategy import generate_signals
n_signals = generate_signals(conn, date(2025, 1, 15))
print(f"signals written: {n_signals}")
```

6. ニュース収集ジョブ実行（RSS から raw_news を収集し銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う有効コード集合 (例: {"7203", "6758", ...})
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)
```

7. J-Quants からデータを直接フェッチする例
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成（主要ファイル）

（src レイアウト想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数・設定管理（.env 自動読み込み）
    - data/
      - __init__.py
      - jquants_client.py              # J-Quants API クライアント（取得 + 保存ユーティリティ）
      - news_collector.py              # RSS ニュース取得・前処理・DB 保存
      - schema.py                      # DuckDB スキーマ定義と初期化
      - stats.py                       # 汎用統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      - features.py                    # data.stats のエクスポート
      - calendar_management.py         # カレンダー管理（営業日判定・更新ジョブ）
      - audit.py                       # 発注監査ログの DDL / 初期化
      - ...                            # その他 data 関連
    - research/
      - __init__.py
      - factor_research.py             # ファクター計算（momentum/volatility/value）
      - feature_exploration.py         # IC/forward returns/summary 等（研究用）
    - strategy/
      - __init__.py
      - feature_engineering.py         # ファクター正規化・features テーブルへの upsert
      - signal_generator.py            # final_score 計算・BUY/SELL 生成・signals 保存
    - execution/
      - __init__.py                    # 発注実行レイヤ（実装は別途）
    - monitoring/                       # （存在が想定される監視モジュール）
    - ... (その他)

---

## 開発・拡張ポイント（参考）

- strategy 層は execution 層に依存しない設計です。実際の発注連携（kabu ステーション等）は execution 層で実装してください。
- features の正規化や signal の重み付けは generate_signals の引数でカスタム可能（weights, threshold）。
- ニュース抽出の銘柄コード検出は簡易な正規表現（4桁）に基づいています。必要に応じてルール拡張してください。
- DuckDB のスキーマは冪等に作成されるため、複数回初期化しても安全です。
- テスト時に .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ライセンス / 貢献

本 README はコードベースの説明用です。実際のライセンスや貢献ルールはリポジトリのルートにある LICENSE / CONTRIBUTING 等のファイルに従ってください（存在する場合）。

---

README に記載した操作例は最小構成に基づきます。実運用ではログ設定・例外処理・ジョブ管理（スケジューラ）・監視・安全対策（レートリミット・リトライ・トークン管理）を十分に実装・確認してください。