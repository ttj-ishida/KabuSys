# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、運用に必要な主要コンポーネントを備えています。

主な設計方針は以下の通りです。
- ルックアヘッドバイアス（Look-ahead bias）防止：各処理は target_date 時点の情報のみを使用
- 冪等性：DB への保存は ON CONFLICT（または同等）で行い、再実行可能
- ネットワーク堅牢性：API リクエストにレートリミット・リトライ・トークン自動刷新等を実装
- テストしやすさ：id_token 等を注入可能にして単体テストが容易

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - raw -> processed レイヤーへの ETL（差分取得、バックフィル対応）
  - DuckDB を使用したデータ永続化（スキーマ初期化関数あり）
- データ品質管理
  - ETL 後の品質チェック（quality モジュールを想定）
- 研究・ファクター計算
  - Momentum / Volatility / Value などのファクター計算（prices_daily, raw_financials を参照）
  - 研究用の IC / forward returns / 統計サマリー関数
- 特徴量生成
  - 生ファクターの正規化（Zスコア）・ユニバースフィルタ適用・features テーブルへのアップサート
- シグナル生成
  - features と ai_scores を統合して最終スコアを算出し BUY/SELL シグナルを生成
  - Bear レジーム判定、エグジット（ストップロス等）ロジックを実装
- ニュース収集
  - RSS 収集、前処理、記事保存、銘柄抽出（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定、次/前営業日検索 等
- 監査ログ（Audit）
  - シグナル→発注→約定のトレースに必要なテーブル定義（order_request の冪等キー等）

---

## 要件

- Python 3.10 以上（ソースでの型ヒント（|）を利用）
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（実運用ではロギング設定や依存に応じた追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン／配置してパッケージをインストールします（編集可能な開発モード推奨）。
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m pip install -e .
   ```

2. 環境変数設定
   - ルートに `.env` / `.env.local` を置くと自動でロードされます（config.py の自動ロード機能）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（config.Settings で要求されるもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API 用パスワード（execution 層で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意（デフォルト値あり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）

   .env の簡単な例（ルートに `.env` として保存）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマの初期化
   Python REPL やスクリプトで初期化します:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成して全テーブルを作成
   # あるいはメモリ DB:
   # conn = init_schema(":memory:")
   ```

---

## 使い方（代表的な操作）

以下は簡単なサンプルコードです。運用用 CLI やジョブは用途に合わせて作成してください。

- 日次 ETL（株価 / 財務 / カレンダー の差分取得と保存）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 1))
print(f"features upserted: {n}")
```

- シグナル生成（features / ai_scores / positions を参照して signals に書き込み）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 1))
print(f"signals created: {count}")
```

- ニュース収集ジョブ（RSS フィード収集 -> raw_news 保存 -> 銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
print(results)
```

- マーケットカレンダー更新（夜間バッチ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants からのデータ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を使用して自動的に取得されます
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
```

---

## 開発メモ / 注意点

- 型アノテーションや一部の API は Python 3.10 以上を想定しています。
- DuckDB へは大量データを一括挿入する設計になっているため、トランザクションやチャンクサイズに注意してください。
- ニュース収集は SSRF 対策、受信バイト数制限（MAX_RESPONSE_BYTES）、gzip 解凍後のサイズチェック等を実装しています。外部から受け取るフィードの安全性を常に意識してください。
- J-Quants API クライアントはレート制限（120 req/min）に合わせたスロットリングとリトライロジックを持ちます。大量リクエストの際は該当部分の調整や監視を行ってください。
- 環境変数読み込みはプロジェクトルート（.git または pyproject.toml の存在）から .env/.env.local を探して自動読み込みします。テスト時など自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュールの構成（src/kabusys 以下の抜粋）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存）
    - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
    - schema.py                  — DuckDB スキーマ定義 & init_schema
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                — ETL パイプライン（差分取得 / run_daily_etl 等）
    - features.py                — data 層の特徴量公開インターフェース
    - calendar_management.py     — マーケットカレンダー管理
    - audit.py                   — 監査ログ用スキーマ
    - pipeline.py                — ETL orchestration
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value 計算
    - feature_exploration.py     — IC・将来リターン・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     — ファクター正規化・features 挿入
    - signal_generator.py        — final_score 計算・signals 挿入
  - execution/                   — 発注関連（空の __init__.py、実装層を想定）
  - monitoring/                  — 監視・通知関連（将来実装想定）

（上記は本リポジトリ内に含まれる主要モジュールの要約です）

---

## ライセンス / 貢献

プロジェクトに対するライセンスや貢献ルールがある場合はルートに配置してください（LICENSE, CONTRIBUTING.md 等）。チーム内で運用する場合は、運用手順・ロール・責任者を明示して運用ルールを定めることを推奨します。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細な設計仕様は各モジュール内の docstring（例: StrategyModel.md, DataPlatform.md 等参照）および該当ドキュメントを参照してください。必要であれば、運用用 CLI、ユニットテストの例、CI/CD ワークフローなどの追補ドキュメントを作成します。