# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得（J‑Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・実行レイヤーのスキーマを含むモジュール群を提供します。本リポジトリは研究・検証から本番（paper/live）運用までを想定した設計になっています。

主な設計方針：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / upsert を基本とする）
- API レート制御・リトライ・トークン自動リフレッシュ
- DuckDB を用いた一貫したローカルデータストア

バージョン: 0.1.0

---

## 機能一覧

- データ取得
  - J‑Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - API レートリミッタ、リトライ、トークン自動更新
- ETL / データプラットフォーム
  - 差分取得（backfill 対応）、品質チェック（quality モジュール）
  - 市場カレンダーの自動更新
- データスキーマ
  - DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution レイヤー）
  - 監査テーブル（signal_events / order_requests / executions 等）
- 特徴量（Feature）生成
  - research による raw factor を正規化・クリップして `features` テーブルへ書き込み
- シグナル生成
  - `features` と `ai_scores` を統合し final_score を計算、BUY／SELL を `signals` に保存
  - Bear レジーム抑制、エグジット（ストップロス等）の判定
- ニュース収集
  - RSS フィードの収集、前処理、記事保存（raw_news）と銘柄紐付け
  - SSRF 対策、gzip 制限、XML パースの堅牢化
- 共通ユーティリティ
  - z-score 正規化、統計ユーティリティ、ランク（Spearman IC 用）

---

## 要件（依存関係）

最低限の Python 環境（3.9+ を想定）。主な依存ライブラリ:

- duckdb
- defusedxml

（実際のパッケージ化時に pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用途）pip install -e . などでローカルパッケージとしてインストール可能

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（`kabusys.config` による自動ロード）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定してください。

必須の環境変数（ライブラリの各機能で利用）:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須：データ取得で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

デフォルト値（未設定時に利用されるパス等）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)

例：.env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 初期化（DuckDB スキーマ作成）

DuckDB データベースを初期化してスキーマを作成します。Python REPL やスクリプトで実行できます。

例（スクリプト）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
print("initialized:", conn)
```

これにより raw_prices / prices_daily / features / signals / ... 等のテーブルとインデックスが作成されます。

---

## 使い方（主要な操作例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1. 日次 ETL（J‑Quants からデータ取得して保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
import datetime

conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=datetime.date.today())
print(res.to_dict())
```

2. 特徴量ビルド（features テーブルの生成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
import datetime

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=datetime.date(2025, 1, 1))
print(f"features upserted: {count}")
```

3. シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
import datetime

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=datetime.date(2025, 1, 1), threshold=0.6)
print(f"signals generated: {n}")
```

4. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードセットを渡すと記事から銘柄を抽出して紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

5. J‑Quants からの直接フェッチ（テストやバッチ処理での利用）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
# settings.jquants_refresh_token が必要
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点：
- ほとんどの処理は target_date 時点のデータのみを参照するよう設計されています（将来情報を使わない）。
- `generate_signals` はデフォルトで重みや閾値を内部デフォルトから補完します。引数で上書き可能です。
- 多くの DB 操作はトランザクションで囲まれ、失敗時はロールバックされます。

---

## 設計上のポイント / 運用メモ

- env の自動ロード: パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を読み込みます。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化は `init_schema()` を一度実行しておくこと（初回だけで OK）。
- J‑Quants API のレート制御は内部で行われるため、通常はアプリ側での追加制御は不要です。ただし大量一括取得を行う場合は注意してください。
- ニュース収集は SSRF 対策やレスポンスサイズ制限を実装済みです。RSS ソースは `DEFAULT_RSS_SOURCES` を参照しますが、引数で上書きできます。
- 監査ログ（audit モジュール）は発注〜約定の連鎖をトレースするためのテーブルを用意しています。実際のブローカー連携は execution 層の実装が必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    ：環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py           ：J‑Quants API クライアント（fetch/save）
  - news_collector.py          ：RSS ニュース収集・保存
  - schema.py                  ：DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py                ：ETL パイプライン（run_daily_etl 等）
  - stats.py                   ：z-score 等統計ユーティリティ
  - features.py                ：data.stats の公開ラッパー
  - calendar_management.py     ：マーケットカレンダー管理
  - audit.py                   ：監査ログスキーマ
  - (その他 quality 等)
- research/
  - __init__.py
  - factor_research.py         ：momentum / volatility / value の計算
  - feature_exploration.py     ：IC / forward returns / summary
- strategy/
  - __init__.py
  - feature_engineering.py     ：features の構築（正規化・クリップ・upsert）
  - signal_generator.py        ：final_score 計算、BUY/SELL 生成、signals への書き込み
- execution/                    ：発注インターフェース（空のパッケージ、実装は必要に応じて）
- monitoring/                   ：モニタリング / 監視用 DB / スクリプト（別途実装）

（上記は本リポジトリ内の主要なモジュールを抜粋した一覧です）

---

## 貢献・開発

- コードは src/ 以下に配置されています。ローカル開発は pip の editable インストール（pip install -e .）を推奨します。
- 新しい ETL ジョブや発注アダプタを追加する際は、既存のトランザクション設計と冪等性（ON CONFLICT）に合わせてください。
- 単体テスト・CI の導入を推奨します（DuckDB のインメモリ DB を使えばテストが容易です: db_path=":memory:"）。

---

何か特定の操作（例: 発注連携の実装例や品質チェックの詳細、CI 設定例）についてドキュメントを追加したい場合は教えてください。必要に応じて README を拡張して、より具体的なチュートリアルや運用手順を追加します。