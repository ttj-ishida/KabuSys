# KabuSys

日本株向けの自動売買システム用ライブラリ（パッケージ）です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査/スキーマ管理など、自動売買プラットフォームの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を構築するためのモジュール群です。主な役割は以下です。

- J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存する（差分更新・ページネーション・リトライ・レート制御対応）
- 取得データを整形して日次 ETL を実行
- 研究（research）で算出した生ファクターを正規化・合成して features テーブルを作成
- features / ai_scores などから売買シグナルを生成して signals テーブルに保存
- RSS を使ったニュース収集と銘柄紐付け
- DuckDB スキーマ定義・初期化、監査ログテーブルの管理
- マーケットカレンダーや営業日計算などのユーティリティ

設計上の重要点:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT で安全に上書き）
- 外部ライブラリ依存を最小限にし、テストやモックが容易な設計

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ）
  - pipeline: ETL ジョブ（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - schema: DuckDB スキーマ定義と init_schema()
  - news_collector: RSS からニュース収集、raw_news / news_symbols 保存
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリーなど
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルに保存
- monitoring / execution / audit や Slack 通知などの準備（設定を通して連携可能）
- 設定管理: kabusys.config.Settings（.env / .env.local / 環境変数読み込み、必須値チェック）

---

## セットアップ手順

※この README はパッケージ内部のコードに基づく手順例です。実際の依存パッケージはプロジェクト側の requirements.txt / pyproject.toml を参照してください。

1. Python と仮想環境の準備
   - 推奨: Python 3.9+（ソースの型注釈に対応するバージョン）
   - 仮想環境作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージのインストール（最小: duckdb, defusedxml）
   ```
   pip install duckdb defusedxml
   ```
   - 実際には requests 等が必要となる可能性があります。プロジェクトの requirements.txt / pyproject.toml を参照してください。

3. パッケージのインストール（開発インストール）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは .git または pyproject.toml を探してルートを決定）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な主な環境変数（config.Settings で必須になっているもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 使用時のパスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル（必須）
オプション:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方

以下は代表的な利用例（Python スクリプト / REPL）です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値を参照
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants からの差分取得と保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"signals written: {count}")
```

5) ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出に使う有効銘柄コードのセット（例: 上場銘柄コードリスト）
results = run_news_collection(conn, known_codes={"7203", "6758", "9984"})
print(results)  # {source_name: saved_count, ...}
```

6) スキーマ接続のみ取得（初期化しない場合）
```python
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
```

エラー処理やジョブの運用は呼び出し側で適切に行ってください。多くの関数は内部でログ出力と例外を行います。

---

## 主要 API（抜粋）

- kabusys.config.settings: 環境変数経由の設定アクセサ
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ作成 + 接続取得
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...): 日次 ETL 完全実行
- kabusys.data.jquants_client.fetch_* / save_*: J-Quants から取得して保存する低レベル関数
- kabusys.research.calc_momentum / calc_volatility / calc_value: ファクター計算
- kabusys.strategy.build_features(conn, target_date): features 作成
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None): signals 作成
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None): RSS 収集ジョブ

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API client（取得・保存）
    - pipeline.py                   — ETL パイプライン
    - schema.py                     — DuckDB スキーマ定義・init_schema
    - news_collector.py             — RSS 収集と保存
    - calendar_management.py        — 営業日判定・カレンダー更新ジョブ
    - features.py                   — features の再エクスポート
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ関連テーブル
    - (その他: quality, monitoring 等が想定)
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py        — IC/forward returns/summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — ファクター正規化・features への upsert
    - signal_generator.py           — final_score 計算 & signals 生成
  - execution/                       — 発注関連（パッケージ化済み）
  - monitoring/                      — 監視・通知用コード（パッケージ化済み）

（実際のファイルはプロジェクト配布版またはリポジトリのルートを参照してください）

---

## 運用上の注意 / ヒント

- デフォルトの DuckDB ファイルは data/kabusys.duckdb。運用環境では適切なパスに設定してください（settings.duckdb_path）。
- .env / .env.local は自動読み込みされます。OS 環境変数 > .env.local > .env の優先順位です。自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）およびリトライロジックは jquants_client に実装されています。大量のデータ取得は注意して行ってください。
- features / signals の処理は target_date を明示的に指定して「その日時点の情報のみ」を使う設計です（ルックアヘッドの防止）。
- news_collector は RSS の XML パースに defusedxml を使用し、SSRF / 大容量レスポンス対策を実装しています。
- ストップロスやエグジット方針などは signal_generator に記載の実装（例: -8% を超える損失で強制売却）を参照してください。実運用前にロジックを十分に検証してください。

---

## 貢献 / テスト

- 追加のユニットテスト、品質チェック、CI 設定などを推奨します。多くのコンポーネントは外部 API やネットワークを利用するため、モック／スタブを使った単体テストが有効です。
- DB 操作は DuckDB を使っているため、テストでは ":memory:" を使ってインメモリで初期化すると高速です。

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

README の内容はコードの実装やプロジェクト方針に基づいて整理しています。追加で「導入手順の詳細」「運用スクリプト例」「CI 設定」「テーブル定義ドキュメント」などが必要でしたら教えてください。