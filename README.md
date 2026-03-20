# KabuSys

日本株向け自動売買（データプラットフォーム＋戦略）ライブラリ / フレームワーク

このリポジトリは、J-Quants API を用いた市場データ取得（ETL）、DuckDB におけるデータスキーマ、ニュース収集、特徴量作成、シグナル生成、監査ログなどを含む日本株自動売買システムの主要コンポーネント群を提供します。

主な目的は「研究→プロダクション」までのワークフローをサポートすることで、データ取得から特徴量作成、シグナル生成、発注前の監査まで一貫して扱えるよう設計されています。

---

## 機能一覧

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、四半期財務データ、JPX 市場カレンダーのページネーション対応フェッチ
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（差分取得・バックフィル）
  - 市場カレンダー、株価、財務データの差分更新
  - 品質チェックフレーム（欠損・スパイク検出等）と分離されたエラーハンドリング
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution レイヤのテーブル定義（冪等）
  - インデックス、制約、監査テーブルを含む包括的スキーマ
- ニュース収集
  - RSS 収集（gzip対応）、XML の安全パース（defusedxml）、SSRF 対策
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256）による冪等保存
  - 記事と銘柄コードの紐付け（抽出ロジック内蔵）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - research モジュールで計算したファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - 正規化ファクター + AI スコアの統合による final_score 計算
  - Bear レジーム判定、BUY/SELL シグナルの生成（冪等で signals テーブルへ保存）
  - エグジット（ストップロス等）の判定ロジック
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリューの計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 統計ユーティリティ（z-score 正規化等）
- 監査ログ（audit）：シグナル→発注→約定のトレーサビリティを保持する監査テーブル群

---

## 必要条件

- Python 3.10 以上（PEP 604 型記法などを使用）
- pip
- （ランタイム依存パッケージ）
  - duckdb
  - defusedxml

開発時は以下のように最低限インストールしてください:

```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# もしパッケージ化されているなら:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## 環境変数 / 設定

kabusys は起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます（環境変数より優先度が低い）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（Settings クラスから）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要時）

その他（オプション／デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作る

```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# （任意）pip install -e .
```

2. 環境変数を用意（プロジェクトルートに .env を配置）

3. DuckDB スキーマ初期化

Python REPL またはスクリプトで以下を実行します:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# これでファイルが作成され、テーブルが初期化されます
conn.close()
```

---

## 基本的な使い方（例）

以下は主要なワークフローの最小例です。実際はログ設定や例外処理を追加してください。

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
conn.close()
```

- 特徴量を作成して features テーブルへ書き込む

```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2026, 1, 31))
print("features upserted:", count)
conn.close()
```

- シグナルを生成して signals テーブルへ書き込む

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2026, 1, 31))
print("signals written:", n)
conn.close()
```

- RSS ニュース収集ジョブの実行例

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと記事→銘柄紐付けを行う
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

- J-Quants からデータを直接フェッチして保存する（テスト用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=None, date_to=None)  # 省略時は範囲指定してください
saved = save_daily_quotes(conn, records)
print(saved)
conn.close()
```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下。実際のリポジトリに合わせて調整してください）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（フェッチ / 保存）
    - news_collector.py — RSS 収集・保存
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - features.py — data.stats の公開ラッパ
    - calendar_management.py — 市場カレンダー操作（営業日判定・更新）
    - audit.py — 監査ログ関連 DDL
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル生成・正規化
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - execution/ — 発注実行層（空の __init__ がある想定）
  - monitoring/ — 監視用コード（SQLite 等を利用する想定、ディレクトリあり）

各モジュールには詳細な docstring が記載されており、設計方針・処理フロー・注意点（ルックアヘッドバイアス回避、冪等性、ログ取得等）が明確に定義されています。

---

## 注意点 / 運用上のヒント

- API トークンは機密情報です。共有リポジトリに直接書かないでください。`.env` / シークレット管理を利用してください。
- DuckDB ファイルは大きくなる可能性があるため、バックアップやディスク容量に注意してください。
- 市場カレンダーがない場合は曜日ベースのフォールバックを行うため、厳密な取引日に依存する処理はカレンダー取得後に行ってください。
- 信号生成や発注ロジックは本番環境（live）と検証（paper_trading）で挙動を分けるため、KABUSYS_ENV を設定して運用してください。
- ニュース収集は外部ネットワークを使用するため、SSRF/サイズチェック等の安全対策が組み込まれていますが、運用時にも通信先の管理を行ってください。
- テストを行う場合、環境変数の自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が便利です。

---

## 今後の拡張 / TODO（概略）

- Execution 層の証券会社 API 実装（kabu ステーション連携）
- リアルタイム・注文キューの実行監視
- バックテスト・評価フレームワークの統合
- AI スコア生成パイプライン（外部モデルとの連携）
- 監視・アラート連携（Slack 通知の実装例）

---

質問や README に追加したい項目があれば教えてください。使用例のコードや .env.example を具体的に作成することもできます。