# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants からマーケットデータや財務データ、RSS ニュースを収集し、DuckDB に保存。研究用ファクター計算、特徴量生成、シグナル生成、ETL パイプライン、カレンダー管理、監査ログなどを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ニュース収集（トラッキング除去 / SSRF 対策 / Gzip 対応）
  - DuckDB への冪等的保存（ON CONFLICT / トランザクション）
- ETL / バッチ処理
  - 日次差分 ETL（市場カレンダー・株価・財務データ）
  - カレンダー更新ジョブ（先読み、バックフィル）
  - 品質チェックフック（quality モジュールと連携）
- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value 等）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン・IC・統計サマリーなどの探索用関数
- 戦略層
  - 特徴量生成（features テーブルへUPSERTする build_features）
  - シグナル生成（features と ai_scores を統合して BUY / SELL シグナルを生成する generate_signals）
- 実行管理（スキーマ）
  - Signals / Orders / Executions / Positions 等の監査向けスキーマ
  - 監査ログ（signal_events, order_requests, executions）によるトレーサビリティ
- ユーティリティ
  - 環境変数 / .env 自動ロード（プロジェクトルート検出）
  - レートリミッタ、再試行ロジック、XML セーフパーサなどの安全対策

---

## 動作要件

- Python 3.10 以上（型アノテーションで union 型を使用）
- 主な依存パッケージ（最小）:
  - duckdb
  - defusedxml

実際のプロジェクトでは追加の依存関係（requests 等）がある場合があります。requirements.txt があればそれを使用してください。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化
   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. 必要パッケージをインストール
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトの requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 設定（環境変数）

kabusys は .env（プロジェクトルート）および .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須 / デフォルト）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（通知機能がある場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

設定はコードから次のように参照できます:
```
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

.env のパースはシェル風の書式（export KEY=val 等）に対応しており、クォートやコメントの取り扱いも行います。

---

## クイックスタート（使用例）

以下は最小限の Python スニペット例です。実行前に必要な環境変数を設定してください。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・株価・財務データを取得して保存）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量の構築（指定日）
```
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date(2024, 1, 5))
print(f"features upserted: {count}")
```

4) シグナル生成（指定日）
```
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, date(2024, 1, 5))
print(f"signals written: {total}")
```

5) RSS ニュース収集
```
from kabusys.data.news_collector import run_news_collection

# known_codes があれば銘柄抽出・紐付けを行う
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) J-Quants からデータを直接取得する（トークンは settings を使用）
```
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
```

---

## 主要モジュールの説明

- kabusys.config
  - 環境変数の管理、自動 .env ロード、設定プロパティ（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・保存関数）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: 日次 ETL（差分取得、品質チェック、結果集約）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 発注〜約定の監査ログスキーマ
  - stats: Z スコア正規化などの統計ユーティリティ
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターを正規化して features テーブルへ UPSERT
  - signal_generator.generate_signals: features + ai_scores を用いて final_score を算出し signals を作成
- kabusys.execution
  - placeholder パッケージ（発注連携ロジックはここに実装）
- kabusys.monitoring
  - 監視・通知系の実装が入る予定の領域

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - audit.py
  - features.py
  - stats.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- strategy/
  - feature_engineering.py
  - signal_generator.py
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - (監視関連モジュール)

ドキュメントや設計ノート（DataPlatform.md, StrategyModel.md 等）がプロジェクトルートにある想定です（コード内コメントで参照）。

---

## 注意点 / 実運用の考慮

- 安全性:
  - RSS 関連は SSRF 対策、XML のセーフパース、レスポンスサイズ制限を実装していますが、本番環境ではさらに監査・監視を行ってください。
- Look-ahead バイアス回避:
  - ファクター/シグナル計算は target_date 時点までの情報のみを使う設計です。データ取得の timestamp（fetched_at）も保存してトレーサビリティを保っています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT で実装されているため、再実行しても重複しにくい設計です。
- 認証トークン:
  - J-Quants のトークンは settings.jquants_refresh_token で管理。jquants_client は自動でリフレッシュ処理を行います（401発生時に一回リトライ）。
- 環境:
  - KABUSYS_ENV による挙動切替（development / paper_trading / live）を意識してログレベルや発注先設定を行ってください。

---

必要に応じて README に次の情報を追加できます:
- CI / テストの実行方法
- 開発ガイド（コーディング規約、PR フロー）
- サンプル .env.example（必須環境変数の雛形）
- 具体的な運用手順（Cron / Airflow / GitHub Actions による定期実行）

追加したい内容があれば教えてください。README を拡張して具体的なコマンド例や .env.example を作成します。