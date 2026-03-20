# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ向け README（日本語）

このドキュメントはソースツリーに含まれる主要モジュールをもとに、プロジェクト概要、機能、セットアップ、基本的な使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームのコンポーネント群です。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダーの取得と DuckDB への保存（ETL）
- ニュース（RSS）収集と記事→銘柄の紐付け
- ファクター計算（モメンタム、ボラティリティ、バリューなど）
- 特徴量の正規化・合成（features テーブル作成）
- シグナル生成（final_score の計算、BUY/SELL シグナルの作成）
- 発注・実行・監査用スキーマ（テーブル定義）
- マーケットカレンダー管理、品質チェック、監査ログ・トレーサビリティのための仕組み

設計上の主な方針は「ルックアヘッドバイアス回避」「冪等性」「外部API呼び出しの堅牢化」「DuckDB を中心としたシンプルな永続化」です。

---

## 機能一覧（主な提供機能）

- data/
  - jquants_client: J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - schema: DuckDB スキーマ定義・初期化（init_schema）
  - pipeline: 日次 ETL（run_daily_etl）・差分取得ロジック
  - news_collector: RSS 収集・前処理・DB 保存（run_news_collection）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Z スコア正規化ユーティリティ
- research/
  - factor_research: モメンタム/ボラティリティ/バリューなどのファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ
- strategy/
  - feature_engineering: features テーブルの構築（build_features）
  - signal_generator: features と ai_scores を統合してシグナル生成（generate_signals）
- execution/（スケルトン）
- monitoring/（監視・ログ関連のための場所）
- config: 環境変数・設定管理（settings オブジェクトを通じて参照）
- audit: 監査ログ（signal_events / order_requests / executions 等）のDDL（スキーマ)

主な API（モジュール関数例）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management.calendar_update_job(conn, lookahead_days=...)

---

## 必要条件

- Python 3.9+（型ヒントに Union 型等使用。実行環境に合わせて適宜）
- パッケージ依存（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

（リポジトリに requirements.txt がない場合は手動で上記パッケージをインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで追加パッケージがあれば requirements.txt を使ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にしたい場合は環境変数を事前に設定:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 省略可能/デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabus_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL / スクリプト内で:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下はライブラリをインポートして使う最小の例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- DB 初期化（再掲）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと今日を使います
print(result.to_dict())
```

- features の構築（研究モジュールのファクターを正規化して features テーブルへ）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"upserted features: {count}")
```

- シグナル生成（features と ai_scores を参照して signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
print(f"signals generated: {total}")
```

- RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 既知の銘柄コードセット（抽出フィルタ）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- カレンダー更新バッチ（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

- 設定値にアクセスする（settings）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意点:
- すべての ETL / 計算関数は「target_date 時点までのデータ」だけを参照する設計で、ルックアヘッドバイアスに配慮しています。
- 多くの保存関数は冪等（ON CONFLICT 等）になっています。
- run_daily_etl や pipeline の関数はエラーハンドリングを含み、部分的失敗時にも他処理を継続する方針です。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要モジュールを抜粋したツリー（src/kabusys）です。実際のツリーはリポジトリ内のファイルに従ってください。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他 execution/monitoring 関連)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視系モジュール)

- README.md（本ファイル）

各モジュールの役割は上の「機能一覧」を参照してください。schema.py にすべての DuckDB テーブル定義（Raw / Processed / Feature / Execution / Audit）が含まれています。

---

## 運用上の注意点 / ベストプラクティス

- 環境変数は秘密情報（トークン等）を含むので `.env` をリポジトリにコミットしないでください。`.env.example` を用意しておくと良いです。
- 本番（live）稼働時は KABUSYS_ENV=live に設定し、デバッグログ等が出ないようにしてください。
- J-Quants API のレート制限や 401 トークン更新の挙動は jquants_client に組み込まれています。API 使用時はログを確認してください。
- DuckDB ファイルは定期的にバックアップを取ってください（単一ファイルのため簡単にバックアップ可能です）。
- news_collector は外部 RSS を取得するためネットワーク・SSRF 対策（スキームチェック、プライベートIPブロック等）を実装していますが、実運用ではさらに監視を行ってください。

---

## 参考（開発者向けメモ）

- 自動 .env ロードは kabusys.config でプロジェクトルート（.git / pyproject.toml）を探索して行われます。テスト・CI で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- 各 ETL / 計算関数は DuckDB の接続オブジェクトを受け取り、SQL と Python の組合せで処理を行います。ユニットテストでは DuckDB の in-memory 接続（":memory:"）を使うと便利です。
- zscore_normalize 等のユーティリティは research と data 両方から参照されるよう分離されています。

---

この README はコードベースの現状（ソース内ドキュメンテーション）をもとに作成しています。追加の運用手順（サービス化、デプロイ、ジョブスケジューラ設定、モニタリング、Slack 通知など）は別途記載してください。必要であればサンプルのデプロイ手順や Dockerfile / systemd ユニット例も作成できます。