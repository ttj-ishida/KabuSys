# KabuSys

日本株自動売買システムのコアライブラリ。データ取得・ETL、ファクター計算、特徴量作成、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。

## 概要
KabuSys は以下の層で構成されたトレーディングプラットフォーム向けの基盤ライブラリです。

- Data layer: J-Quants からの株価・財務・カレンダーなどの取得、DuckDB への永続化（冪等保存）
- Processed / Feature layer: prices_daily / features / ai_scores 等の加工済みデータ
- Strategy layer: 特徴量の正規化（Zスコア）・合成、売買シグナル生成
- Execution / Audit layer: シグナル／注文／約定／ポジション等を記録するスキーマ（監査トレーサビリティ）

設計方針として、ルックアヘッドバイアス対策、API レート制御、冪等性、トランザクションによる原子性、外部依存の最小化（可能な限り標準ライブラリ）を重視しています。

## 主な機能
- J-Quants API クライアント（取得・リトライ・レート制限・トークン自動リフレッシュ）
- DuckDB スキーマ定義と初期化（init_schema）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（momentum / volatility / value 等）
- 特徴量作成（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（最終スコア合成、Bear レジーム抑制、エグジット判定）
- RSS ベースのニュース取得・正規化・DB 保存・銘柄抽出
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ用スキーマ（signal_events / order_requests / executions 等）

## 必要条件
（実行環境に応じて適宜追加してください）
- Python 3.9+
- duckdb
- defusedxml

（パッケージ化時は pip の requirements.txt / pyproject.toml を参照してください）

## セットアップ手順

1. リポジトリをチェックアウトし、パッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な Python パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートに `.env`（または `.env.local`）を作成してください。主要な環境変数は次節を参照。

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから実行します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # デフォルトパスは data/kabusys.duckdb
   conn.close()
   ```

※ テストや CI で自動環境変数のロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。パッケージインポート時に .env の自動読み込み処理がスキップされます。

## 環境変数（主な一覧）
config.py で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

必須変数が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。`.env.example` を用意している場合はそれを参考に `.env` を作成してください（リポジトリにない場合は README に沿って追加してください）。

## 基本的な使い方

### DB 初期化（例）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを作成
```

### 日次 ETL 実行（J-Quants から差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

run_daily_etl は calendar → prices → financials → 品質チェック（オプション）を順に実行し、ETLResult を返します。

### 特徴量ビルド（features テーブルへの保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {n}")
```

build_features は calc_momentum / calc_volatility / calc_value を利用し、ユニバースフィルタ・Zスコア正規化・±3 クリップを行って features テーブルへ日付単位で置換（冪等）保存します。

### シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31))
print(f"signals generated: {count}")
```

generate_signals は features と ai_scores を統合して最終スコアを計算し、BUY / SELL シグナルを signals テーブルへ日付単位で置換保存します。

### ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 既知の銘柄コードセット（任意）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

fetch_rss / save_raw_news / save_news_symbols を組み合わせてニュース収集と銘柄紐付けを行います。

## 監査・実行フロー
- signal_events（戦略が生成したシグナル） → order_requests（発注要求: 冪等キー） → executions（証券会社約定）
- すべてのテーブルは created_at / updated_at を持ち、監査証跡を残します。

## 開発・テスト
- 設定の自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のインメモリ DB を使う場合は db_path に ":memory:" を指定可能
- 外部 API 呼び出し箇所（jquants_client._request、news_collector._urlopen 等）はユニットテストでモック可能に設計されています

## ディレクトリ構成
（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - news_collector.py      — RSS 収集 / 前処理 / DB 保存
    - calendar_management.py — カレンダー管理（is_trading_day 等）
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログスキーマ DDL（signal_events 等）
    - ...（quality 等の補助モジュールが想定される）
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — IC / forward returns / summary 等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（ユニバースフィルタ・正規化）
    - signal_generator.py    — final_score 計算と signals 作成
  - execution/               — 発注層（未実装ファイル群のプレースホルダ）
  - monitoring/              — 監視用（SQLite 組み込み等、未実装プレースホルダ）

（実際のファイルは src/kabusys 以下を参照してください）

## 注意事項
- J-Quants や証券会社の API キー・パスワードは機密情報です。 `.env` ファイルはバージョン管理に含めないでください。
- 本ライブラリは発注ロジック（実際の注文送信）を直接含まないことを意図しています（execution 層を分離）。実運用ではリスク管理・注文フローの検証が必須です。
- production（live）モードでは特に安全対策（監査ログ、二重送信回避、ストップロス等）の動作確認を十分行ってください。

---

質問や追加したいドキュメント（API リファレンス、運用手順、デプロイ手順、テストガイド等）があればお知らせください。必要に応じてサンプルスクリプトや CI/CD 用の説明も作成します。