# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants から市場データを収集して DuckDB に保存し、研究用のファクター計算・特徴量作成・シグナル生成を行うことを主な目的としています。発注・実行（execution）や監視（monitoring）などの実運用レイヤーを想定したスキーマ・ユーティリティ群も含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- 設定（環境変数）
- ディレクトリ構成
- 補足・注意事項

---

## プロジェクト概要

KabuSys は次のような要素で構成されています。

- J-Quants API クライアント（レート制御・リトライ・認証リフレッシュ機能付き）
- DuckDB に対するスキーマ定義と初期化ユーティリティ
- ETL（市場カレンダー／日足／財務データ等）パイプライン
- ニュース収集（RSS）と銘柄抽出・保存機能
- ファクター計算（Momentum / Volatility / Value）と特徴量エンジニアリング
- シグナル生成ロジック（ファクター + AI スコアを統合）
- 監査ログ用テーブル（発注〜約定トレース用）の定義
- 研究用ユーティリティ（将来リターン計算、IC、統計サマリー等）

設計方針としては「ルックアヘッドバイアスの抑制」「冪等性」「外部依存を最小化（標準ライブラリ中心）」が貫かれています。

---

## 機能一覧

- データ取得
  - J-Quants API から日足・財務・カレンダーをページネーション対応で取得
  - API 呼び出しは固定間隔スロットリング（120 req/min）で制御
  - 認証トークン自動リフレッシュ（401 時）と指数バックオフによるリトライ
- データ保存
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装
- ETL
  - 差分更新・バックフィル（最終取得日から再取得）をサポート
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・スパイク検出など）を呼び出せる設計
- 研究・戦略
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - Zスコア正規化ユーティリティ
  - 特徴量作成（ユニバースフィルタ、正規化、日付単位の UPSERT）
  - シグナル生成（コンポーネントスコアの重み付け合算、BUY/SELL の判定）
- ニュース収集
  - RSS フィード取得、XML パース（defusedxml）、URL 正規化、記事ID生成、銘柄抽出
  - SSRF 対策、受信サイズ上限、gzip 対応
- カレンダー管理
  - 営業日判定・次/前営業日取得・範囲の営業日列挙
- 監査（audit）スキーマ群
  - signal_events / order_requests / executions 等の監査用テーブル定義

---

## セットアップ手順

前提
- Python 3.10 以降（コード中での型合成（|）や型ヒントに対応するため）
- DuckDB を利用するため、ネイティブ拡張が必要です（pip でインストール可能）

1. リポジトリをクローンまたはソースを配置する
2. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください）
3. 環境変数の設定
   - プロジェクトルートに `.env`（およびローカル上書き用に `.env.local`）を作成できます。
   - KabuSys の config モジュールは自動で .env を読み込みます（詳細は下の「設定」参照）。
4. データベース初期化（DuckDB スキーマを作成）
   - Python REPL やスクリプトで次を実行します:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
     この操作で必要なテーブルとインデックスが作成されます。

備考:
- 自動的な .env 読み込みを無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。

---

## 使い方（簡単な例）

以下は主要な処理の最小例です。実行は Python スクリプトや CLI のラッパーで行う想定です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（市場カレンダー・日足・財務データの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は init_schema の戻り値（DuckDB 接続）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

4) ニュース収集（RSS）ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を与えると記事-銘柄の紐付けを試みる
known_codes = {"7203", "6758", "9984"}  # など
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) 特徴量作成（feature engineering）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date.today())
print("built features:", n)
```

6) シグナル生成
```python
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", count)
```

注意:
- すべての公開 API は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ります。
- ETL / データ取得関数は id_token を注入可能で、テスト容易性を考慮しています（省略時は内部キャッシュを使用）。

---

## 設定（環境変数）

自動ロード対象: プロジェクトルートの `.env` → `.env.local`（`.env.local` が優先で上書き）  
（ただし OS 環境変数が優先され、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化）

主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API のパスワード
  - KABU_API_BASE_URL (オプション) — デフォルト: http://localhost:18080/kabusapi
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- 実行環境 / ログ
  - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）

設定が不足している必須キーを参照すると Settings クラスが ValueError を投げます。`.env.example` を参考にしてください（存在する場合）。

---

## ディレクトリ構成

主要ファイル／モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（自動 .env ロード機能含む）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・保存ユーティリティ）
    - news_collector.py
      - RSS フィード収集、正規化、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
    - calendar_management.py
      - 営業日判定・calendar_update_job 等
    - features.py
      - data.stats の再エクスポート
    - audit.py
      - 監査ログ用スキーマ DDL（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py
      - 将来リターン計算、IC、summary、rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - ファクター正規化・ユニバースフィルタ・features テーブルへの upsert
    - signal_generator.py
      - final_score 計算、BUY/SELL の判定、signals テーブルへの upsert
  - execution/
    - __init__.py
    - （実行層の実装は想定されているがコードベース内では最小に留まる）
  - monitoring/
    - （監視用 DB / ロギング連携のユーティリティを配置する想定）

（各モジュール内の docstring に詳細な設計方針・仕様が記載されています）

---

## 補足・注意事項

- Python バージョンは 3.10 以上を想定しています（型ヒントの表記など）。
- J-Quants API はレート制限が厳しいため、jquants_client は固定間隔スロットリングを実装しています。複数プロセスや別クライアントと併用する場合はレートに注意してください。
- ニュース収集モジュールは SSRF 対策 / XML パースの安全化 / レスポンスサイズ制限 等の防御を実装していますが、実運用ではさらに監視と監査が必要です。
- シグナル生成・発注ロジックはリスク管理や資金管理の実装次第で振る舞いが大きく変わるため、paper_trading 環境で十分に検証してから live 適用してください。
- データベース・ファイルのパスは Settings により変更可能です。バックアップやアクセス権に注意してください。
- 本 README はコード内の docstring を元に整理した簡易ドキュメントです。より詳細な設計資料（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がプロジェクトにある場合はそちらを参照してください。

---

必要があれば、README に以下を追加できます:
- 具体的な .env.example のテンプレート
- CI / テストの実行方法
- よくあるトラブルシュート（認証エラー、DB ロック等）
- 開発フロー（ブランチ戦略、バージョニング）