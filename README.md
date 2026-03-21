# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータプラットフォームと戦略実行層を備えた自動売買システムのライブラリです。データ収集（J-Quants, RSS）、DuckDB ベースのデータスキーマ、ファクター計算・特徴量生成、シグナル生成、ETL パイプラインなどをモジュール化して提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ設計（各計算は target_date 時点の情報のみを使用）
- DuckDB を用いたローカル DB（軽量で高速な分析向け）
- 冪等性（ON CONFLICT / idempotent 保存）とトランザクション管理
- 外部 API 呼び出し（J-Quants 等）へはレート制御・リトライ・トークン自動更新を実装
- セキュリティ考慮（RSS の SSRF 対策、defusedxml による XML パース安全化）

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings）

- データ取得・保存（data/）
  - J-Quants API クライアント（jquants_client）
    - 株価日足、財務データ、マーケットカレンダー取得
    - レートリミット管理、リトライ、トークン自動リフレッシュ
  - ニュース収集（news_collector）
    - RSS フィード取得、テキスト前処理、記事ID生成、銘柄抽出、DB 保存
    - SSRF 対策・受信サイズ制限・XML 安全パース
  - DuckDB スキーマ定義・初期化（schema）
    - Raw / Processed / Feature / Execution 層のテーブル定義
  - ETL パイプライン（pipeline）
    - 差分取得、保存（idempotent）、品質チェックフック
  - 市場カレンダー管理（calendar_management）
    - 営業日判定、next/prev/trading days、夜間更新ジョブ
  - 統計ユーティリティ（stats）
    - クロスセクション Z スコア正規化等

- リサーチ（research/）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- 戦略層（strategy/）
  - 特徴量組成（feature_engineering.build_features）
    - research で計算した raw factor を統合・正規化して features テーブルへ保存
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成・signals テーブルへ保存
    - Bear レジーム抑制、エグジット判定（ストップロス等）

- 実行・モニタリング（execution/, monitoring/）
  - 現在はパッケージエントリが用意されています（実装拡張向け）

---

## 必要な環境・依存パッケージ

- Python 3.9+（型ヒントに | を使用しているため 3.10+ が推奨されますが、コードは 3.9 互換に配慮）
- duckdb
- defusedxml
- （標準ライブラリで多くを賄っていますが、HTTP/URL 処理は urllib を使用）

インストール例（仮に setuptools / poetry 等でインストール可能な場合）:
```bash
pip install duckdb defusedxml
# ローカル開発: パッケージルートで
pip install -e .
```

---

## 環境変数（必須 / 任意）

自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な必須環境変数：
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）：
- KABU_API_BASE_URL — kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

設定はコード上で `from kabusys.config import settings` によって取得できます。

例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

未設定の必須変数にアクセスすると ValueError が発生します。

---

## セットアップ手順（ローカルで動かすための最小手順）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存をインストール
   - pip install duckdb defusedxml
   - （プロジェクトで配布されている場合は pip install -e .）
4. プロジェクトルートに .env を作成（.env.example を参考に）
   - 必須トークン類を設定する
5. DuckDB スキーマを初期化
   - Python コンソールまたはスクリプトで init_schema を呼ぶ:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要なワークフロー例）

以下は代表的な日次ワークフローです。

1. DuckDB の初期化（上記）
2. 日次 ETL（株価・財務・カレンダーの差分取得・保存・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3. 特徴量の構築（feature_engineering）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today())
print(f"signals written: {count}")
```

5. ニュース収集ジョブ（news_collector.run_news_collection）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使う銘柄セット（例: 全上場銘柄コードの set）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)
```

注意:
- これらの関数は DuckDB 接続を受け取りトランザクションを内部で扱います。
- production 実行時は KABUSYS_ENV を `live` に設定し、ログ・監視設定を適切に行ってください。

---

## 主要モジュールの説明（簡潔）

- kabusys.config
  - 環境変数ロード・検証。自動で .env/.env.local をプロジェクトルートから読み込む。
- kabusys.data.jquants_client
  - J-Quants API を呼ぶクライアント。レートリミット、リトライ、トークン取得機構を内蔵。
- kabusys.data.news_collector
  - RSS 取得 → 前処理 → raw_news に保存 → 銘柄紐付け処理を提供。
- kabusys.data.schema
  - DuckDB のテーブル定義と init_schema / get_connection を提供。
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）, 個別 ETL ジョブ（prices/financials/calendar）を提供。
- kabusys.research
  - factor_research: momentum/volatility/value ファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリ等
- kabusys.strategy
  - feature_engineering.build_features: features テーブル作成
  - signal_generator.generate_signals: final_score 計算・signals テーブル出力

---

## ディレクトリ構成

（本 README は src/kabusys 以下のファイル群に基づきます）

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
      - audit など（実行層関連）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/      (発注・ブローカー連携用、現状はパッケージ化)
    - monitoring/     (監視/メトリクス用、拡張用)

---

## 開発・拡張に関する注意点

- DB スキーマは DuckDB 用に設計されています。初回は init_schema() を必ず呼んでください。
- 外部 API（J-Quants）を叩く関数は idempotent（ON CONFLICT）で保存しますが、トークン・API レートに注意してください。
- RSS フィード取得では SSRF / XML 攻撃・大容量レスポンス対策が実装されています。外部からフィード URL を受け付ける場合は既知ソースのみ許可することを推奨します。
- strategy 層は execution 層（ブローカー送信）に依存しないように設計されています。execution 実装を接続して発注フローを作成してください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境読み込みを抑制できます。

---

もし README に含めたい追加のセクション（例: API リファレンス、実行例スクリプト、CI/デプロイ手順）があればお知らせください。README を用途に合わせて拡張します。