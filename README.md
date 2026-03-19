# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・前処理・特徴量生成・シグナル作成を行う自動売買プラットフォームのライブラリです。J-Quants API や RSS ニュースを取り込み、DuckDB 上で ETL → ファクター計算 → シグナル生成 を行うためのモジュール群を備えています。

---

## プロジェクト概要

主な目的:
- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存
- 取得データの品質チェック、加工（prices_daily / fundamentals など）
- 研究（research）で得られた生ファクターの正規化・合成（feature 層）
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成
- RSS フィードからニュースを収集し、記事と銘柄コードを紐付けて保存
- 発注・約定・ポジションなど監査ログを保持するスキーマ設計

設計上の特徴:
- DuckDB をデータストアとして使用（オンディスク / インメモリ対応）
- J-Quants API 呼び出しに対してレートリミット、リトライ、トークン自動リフレッシュを実装
- ETL・DB 保存は冪等（ON CONFLICT / トランザクション）で安全
- ルックアヘッドバイアス防止のため「target_date 時点のみ」を使う設計
- RSS 取得時の SSRF 防御、XML 爆弾対策（defusedxml）等の堅牢性考慮

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン管理）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・backfill・品質チェック）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - stats: Zスコア正規化など統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）等の探索ツール
- strategy/
  - feature_engineering.build_features: 生ファクターの正規化・features テーブル作成
  - signal_generator.generate_signals: features と ai_scores を統合して signals を生成
- execution / monitoring: （発注・監視に関するプレースホルダ／モジュール群）
- config: 環境変数読み込みと Settings（.env 自動ロード、必須変数の検証）
- audit: 発注〜約定をトレース可能にする監査ログテーブル（order_requests, executions 等）

主要な設計上の取り決めや定数（抜粋）:
- ユニバース最小株価: 300 円
- ユニバース最小売買代金: 5 億円
- Z スコアは ±3 でクリップ
- デフォルト BUY 閾値: 0.60
- J-Quants API: 120 req/min のレートリミット（モジュールで制御）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法（X | Y）を利用）
- DuckDB と defusedxml を含む依存ライブラリ

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトをパッケージ化している場合は pip install -e .）

   例（開発時）:
   - pip install -e ".[dev]"  # もし setup/pyproject で extras を用意している場合

3. 環境変数 / .env を用意
   プロジェクトルート（リポジトリ直下）に `.env` または `.env.local` を置くと自動で読み込みされます（ただしテスト時などに自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   最低限設定すべき環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb  # 省略時のデフォルト
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   .env の書式はシェルライク（export KEY=val, クォート対応、コメント行対応）で読み込まれます。

4. データベース初期化（DuckDB）
   Python スクリプトから以下を実行してスキーマを作成します:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   これにより必要な全テーブルとインデックスが作成されます。

---

## 使い方（簡単なコード例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の返り値）を受け取ります。

1) DB 初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
# conn は DuckDB 接続
n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
# threshold / weights を渡して挙動をカスタマイズ可能
count = generate_signals(conn, target_date=date(2025, 1, 15), threshold=0.6)
print(f"signals created: {count}")
```

5) ニュース収集ジョブ（RSS フィードを DB に保存して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は取引対象の銘柄コード集合（例: {'7203','6758',...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) J-Quants からのデータ取得（直接呼ぶ場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

7) 設定値へアクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- 多くの操作（ETL、feature/build、signal/generate）は「target_date 時点の情報のみ」を使うことでルックアヘッドバイアスを避ける設計です。
- J-Quants API はレート制限・リトライ・401 自動リフレッシュを内包しています。refresh token は環境変数 JQUANTS_REFRESH_TOKEN で与えてください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py                  - パッケージ情報（__version__）
- config.py                    - 環境変数読み込み・Settings
- data/
  - __init__.py
  - jquants_client.py          - J-Quants API クライアント（fetch/save 関数）
  - schema.py                  - DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py                - ETL パイプライン（run_daily_etl など）
  - news_collector.py          - RSS 収集・保存・銘柄抽出
  - calendar_management.py     - 市場カレンダー管理ユーティリティ
  - features.py                - zscore_normalize の再エクスポート
  - stats.py                   - zscore_normalize 他統計ユーティリティ
  - audit.py                   - 監査ログ用スキーマ DDL（発注→約定のトレース）
- research/
  - __init__.py
  - factor_research.py         - momentum/value/volatility 等の計算
  - feature_exploration.py     - forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py     - build_features（正規化・features へ UPSERT）
  - signal_generator.py        - generate_signals（final_score 計算・BUY/SELL 判定）
- execution/                    - 発注・約定層（プレースホルダ）
- monitoring/                   - 監視関連（プレースホルダ）

補足:
- docs/*.md（設計ドキュメント参照: StrategyModel.md, DataPlatform.md 等）が参照される設計ですが、コード内に該当仕様のコメントが埋め込まれています。
- テーブル定義やチェック条件（CHECK, PRIMARY KEY）は schema.py に詳細記載。

---

## 運用上の注意 / ヒント

- 自動環境読み込み:
  - プロジェクトルート（.git や pyproject.toml を基準）に置かれた `.env` / `.env.local` が自動ロードされます。
  - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト用途など）。

- J-Quants トークン:
  - get_id_token() は refresh token を使って id token を取得します。トークンは内部キャッシュされ、401 時に自動リフレッシュします。

- ETL の差分更新:
  - run_prices_etl / run_financials_etl は DB の最終取得日を元に差分を取得し、既に最新の場合は何もしません。デフォルトで backfill_days=3 により直近数日の再取得を行い API 側の後出し修正を取り込みます。

- テスト:
  - ネットワーク呼び出しを伴う箇所（jquants_client、news_collector._urlopen 等）はモックしやすい構造になっています（id_token の注入、内部関数の差し替え等）。

---

README に書かれている使い方はライブラリの主要な機能を紹介するためのサンプルです。詳細な API や設計仕様（StrategyModel.md / DataPlatform.md 等）はコード内コメント・別ドキュメントを参照してください。質問や特定の機能のドキュメント化が必要であればお知らせください。