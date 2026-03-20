# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ・スキーマ定義など、戦略開発から発注準備までの主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB を内部データベースとして使い、J-Quants API などから取得したデータを蓄積・整形し、戦略向けの特徴量（features）と売買シグナル（signals）を生成するためのモジュール群をまとめたパッケージです。  
研究（research）用のユーティリティや、RSS を用いたニュース収集、JPX カレンダー管理、ETL バッチ処理、監査ログ用スキーマなどを含みます。設計は冪等性（idempotent）・ルックアヘッドバイアス回避・安全な外部アクセス制御を重視しています。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価、財務データ、JPX カレンダーの取得（ページネーション・リトライ・レート制御・トークン自動更新対応）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- ETL パイプライン
  - 差分取得、バックフィル対応、品質チェックフレームワークとの統合
  - 日次 ETL ジョブ（run_daily_etl）
- データスキーマ管理
  - DuckDB 用のスキーマ初期化・接続ユーティリティ（init_schema / get_connection）
  - 生データレイヤー／加工レイヤー／特徴量／実行レイヤーを定義
- 研究用ユーティリティ（research）
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 研究で作成した生ファクターを正規化・ユニバースフィルタ・クリップ処理して features テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定、エグジット（ストップロス等）判定を含む
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理・記事 ID 正規化（SHA-256）・raw_news 保存・銘柄抽出と紐付け
  - SSRF 対策・XML の安全パース・レスポンスサイズ制限等の防御処理
- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダー取得・営業日判定・次/前営業日検索等
- 監査ログ（data.audit）
  - signal → order_request → executions までのトレース用テーブル定義
- 共通統計ユーティリティ（data.stats）
  - クロスセクション Z スコア正規化 等

---

## 必要条件

- Python 3.10 以上（モジュール内の型注釈（| 型）や機能に依存）
- 主要依存パッケージ（一例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

※ 実際の依存はプロジェクトの pyproject.toml / requirements.txt を確認してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. パッケージと依存をインストール（ローカル開発インストール）
   ```
   pip install -U pip
   pip install -e ".[dev]"   # もし pyproject / extras が用意されている場合
   # もしくは最低限:
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動読み込みされます（config モジュールが .git / pyproject.toml を基準に検索）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     # 任意:
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB とスキーマを作成します。
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルパス（デフォルト: data/kabusys.duckdb）
   ```

---

## 使い方（主要な例）

以下は代表的なモジュールの使い方例です。実行はプロジェクトの仮想環境内で行ってください。

- DuckDB に接続する（既存DB）
```python
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
```

- スキーマを初期化する
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務の差分取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量をビルドして features テーブルへ保存
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {count}")
```

- シグナル生成（features / ai_scores / positions を参照して signals を作る）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025,3,1), threshold=0.6)
print(f"signals written: {total}")
```

- ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- JPX カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの処理は冪等性を保証するよう設計されています（同日付の再実行で重複を上書きまたはスキップ）。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 DB（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ（値が設定されていれば無効化）

.env の自動読み込み順序:
- OS 環境変数 > .env.local > .env（プロジェクトルートの .git または pyproject.toml を起点に探索）

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py              — RSS 収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                    — ETL パイプライン（run_daily_etl など）
    - calendar_management.py         — JPX カレンダー管理
    - audit.py                       — 監査ログスキーマ
    - features.py                     — features 再エクスポート
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — IC, forward returns, summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py         — features を作成する処理
    - signal_generator.py            — final_score 計算・BUY/SELL 生成
  - execution/                        — 発注関連（プレースホルダ）
  - monitoring/                       — 監視・メトリクス系（プレースホルダ）
- pyproject.toml / setup.cfg / requirements.txt（存在する場合）

---

## 開発・貢献

- コードは型注釈とドキュメンテーション文字列により設計意図を明確にしています。ユニットテスト・型チェック（mypy）・静的解析（flake8 等）を導入すると良いです。
- 外部 API キーやパスワードは .env に保存し、`.gitignore` に追加してください。
- 実運用（ライブ発注）では必ず paper_trading で入念に検証し、監査ログと二重チェックを組み合わせてください。

---

## 注意事項

- 実際の資金を用いた売買を行う場合は、リスク管理・発注の安全性（冪等性・オフセット・注文サイズ管理等）を必ず実装してください。本パッケージはあくまで基盤・ツール群を提供するものであり、完全な運用用トレードシステムではありません。
- J-Quants API 利用規約・レート制限を順守してください（本コードは 120 req/min を想定した RateLimiter を含みます）。
- 外部ネットワークアクセス（RSS 等）では SSRF や XML 攻撃を考慮した実装がされていますが、運用環境のネットワークポリシーに合わせて更なる制限を検討してください。

---

この README はコードベースの主要機能と導入方法を簡潔にまとめたものです。より詳細な設計仕様（StrategyModel.md, DataPlatform.md, DataSchema.md 等）がリポジトリに含まれている場合はそちらも参照してください。