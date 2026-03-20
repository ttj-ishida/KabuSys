# KabuSys

日本株向け自動売買・データプラットフォームライブラリ (kabusys)
バージョン: 0.1.0

短い説明:
- J-Quants などからマーケットデータを収集して DuckDB に蓄積し、
  特徴量作成、戦略シグナル生成、ニュース収集、発注トレーサビリティまでを想定した
  モジュール群を提供します。
- 研究（research）用途と本番（execution）用途を分離し、ルックアヘッドバイアスや冪等性に配慮した設計です。

---

## 主な機能一覧

- データ収集（J-Quants API クライアント）
  - 日次株価（OHLCV）、財務データ、JPXマーケットカレンダーの取得（ページネーション・リトライ・レート制御対応）
- ETLパイプライン
  - 差分取得、バックフィル、品質チェック、日次バッチ run_daily_etl
- データ管理（DuckDB スキーマ定義・初期化）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
- ニュース収集
  - RSS フィードの取得、前処理、記事ID生成、銘柄抽出、DB保存（SSRF対策・GZip上限・トラッキング除去など）
- 研究用ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン計算、IC計算、統計サマリー
- 特徴量エンジニアリング
  - research の生ファクターを正規化・合成して features テーブルへ UPSERT（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成（冪等）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査・トレーサビリティ（audit）
  - signal_events / order_requests / executions など監査用テーブル群
- 汎用統計ユーティリティ（zscore 等）

---

## 動作要件

- Python >= 3.10（型注釈で `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- （実行時に J-Quants API や RSS の取得にネットワーク接続が必要）

依存関係はプロジェクトの packaging / requirements に合わせてインストールしてください。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合は pip install -e . や requirements.txt を使用）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要 API の例）

以下はライブラリ内関数の使い方サンプルです（簡易的な例）。

1) DuckDB スキーマ初期化
- Python REPL やスクリプトから:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

2) 日次 ETL 実行（J-Quants から差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

4) シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", n)
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続は init_schema / get_connection で取得してください。
- 多くの処理は冪等（idempotent）設計で、複数回実行しても重複データを書きこまないようにしています（ON CONFLICT 等）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境 (development|paper_trading|live)
- LOG_LEVEL (任意) — ログレベル

自動的に .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

（ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - news_collector.py              — RSS ニュース収集 / 前処理 / DB保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - stats.py                       — 統計ユーティリティ (zscore 等)
    - pipeline.py                    — ETL パイプライン（run_daily_etl 他）
    - features.py                    — features API 再エクスポート
    - calendar_management.py         — カレンダー管理・ジョブ
    - audit.py                       — 監査ログ用スキーマ / 初期化
    - (その他モジュール)
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（mom/vol/value）
    - feature_exploration.py         — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features の構築（正規化・フィルタ）
    - signal_generator.py            — signals の生成ロジック
  - execution/                       — 実行（発注）層（パッケージ用意）
  - monitoring/                      — 監視・モニタリング用（データ格納等）
  - その他モジュール...

---

## 設計上の注意点 / ポリシー

- ルックアヘッドバイアス回避: 戦略・研究モジュールは target_date 時点の情報のみを用いる設計です。
- 冪等性: ETL・保存処理は ON CONFLICT 等を用いて冪等になるよう実装されています。
- セキュリティ: RSS 取得では SSRF 対策 / gzipped レスポンスサイズ制限 / XML パースに defusedxml を利用。
- ロギング: 各モジュールは logger を利用。LOG_LEVEL で制御してください。
- テスト容易性: id_token の注入や内部関数のモックができる設計です。

---

## 貢献 / 問い合わせ

- バグ報告・機能改善は issue を作成してください。
- 大きな設計変更は事前に Issue で相談してください。

---

README は以上です。必要であればセットアップの具体的な requirements.txt、CI / 実行スクリプト、あるいはより詳細な開発者向けドキュメント（API リファレンス、StrategyModel.md / DataPlatform.md の抜粋）を追加できます。どの情報を補完しますか？