# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
DuckDB を用いたデータレイヤ、J-Quants API 経由のデータ収集、研究用のファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログなどの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（計算は target_date 時点の情報のみを使用）
- 冪等性（DB への保存は ON CONFLICT 等で重複を排除）
- テストしやすさ（id_token 注入、モジュール単位の分離）
- 外部 API 呼び出しは data 層に限定し、strategy 層は発注層に依存しない

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード、必須設定の取得（kabusys.config）
- データ収集（J-Quants API）
  - 株価日足、財務データ、マーケットカレンダーの取得・保存（kabusys.data.jquants_client）
  - ETL パイプライン（日次差分取得・バックフィル・品質チェック）（kabusys.data.pipeline）
  - DuckDB スキーマ初期化 / 接続管理（kabusys.data.schema）
- ニュース収集
  - RSS フィード取得・前処理・保存・銘柄抽出（kabusys.data.news_collector）
  - SSRF / XML Bomb / 大容量対策の実装
- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）（kabusys.research.factor_research）
  - 将来リターン計算、IC 計算、統計サマリ（kabusys.research.feature_exploration）
- 特徴量エンジニアリング / 戦略
  - ファクター正規化・ユニバースフィルタ・features テーブルへの保存（kabusys.strategy.feature_engineering）
  - 正規化済みファクター＋AI スコア統合 → final_score 計算、BUY/SELL 信号生成（kabusys.strategy.signal_generator）
- 統計ユーティリティ
  - Z スコア正規化など（kabusys.data.stats）
- マーケットカレンダー管理（is_trading_day, next_trading_day など）
- 監査ログ（signal / order / execution のトレーサビリティ設計）

---

## 必要要件

- Python 3.10+
- 主な外部パッケージ:
  - duckdb
  - defusedxml

（プロジェクトで使用される他のパッケージがあれば requirements.txt を追加してください）

---

## 環境変数

下記の環境変数を設定してください（必須・任意が混在します）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)。未設定は development
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=~/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb defusedxml
   - （開発用） pip install -e .

3. 環境変数を設定（.env をプロジェクトルートに配置）
   - .env または環境変数で上記必須値を設定してください。
   - パッケージ起動時に .env / .env.local が自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。

4. DuckDB スキーマ初期化:
   - Python REPL やスクリプトから:
     ```
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
     ```
   - ":memory:" を渡すとインメモリ DB になります。

---

## 使い方（主要ワークフロー）

以下は代表的なワークフロー（ETL → 特徴量生成 → シグナル生成）のコード例です。

1) ETL（デイリー）
```
from datetime import date
import duckdb
from kabusys.data import pipeline, schema
from kabusys.config import settings

# DB 初期化（既に初期化済みなら既存ファイルを使う）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL 実行（デフォルトは今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（features テーブルを作成）
```
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"built features for {n} codes")
```

3) シグナル生成（signals テーブルに BUY/SELL を書き込む）
```
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"{count} signals generated")
```

4) ニュース収集と銘柄紐付け
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット（DB から取得するのが望ましい）
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: new_saved_count, ...}
```

5) J-Quants クライアントを直接使う（テストやカスタム取得）
```
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存するには conn を渡して jq.save_daily_quotes(conn, records)
```

---

## ディレクトリ構成

以下はソースツリーの概略（重要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & 保存ロジック
    - news_collector.py              -- RSS ベースのニュース収集・保存
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - features.py                    -- features 再エクスポート
    - calendar_management.py         -- market_calendar 管理 / 営業日判定
    - audit.py                       -- 監査ログ（order/signals/executions）
    - ...（その他 data 層モジュール）
  - research/
    - __init__.py
    - factor_research.py             -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py         -- IC / 将来リターン / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py         -- features 構築（正規化・ユニバースフィルタ）
    - signal_generator.py            -- final_score 計算・BUY/SELL 生成
  - execution/                       -- 発注・ブローカー連携（empty placeholder）
  - monitoring/                      -- 監視／通知関連（placeholder）

---

## 注意点 / 運用上のポイント

- 環境（KABUSYS_ENV）に応じて live / paper_trading / development の挙動を切り替えてください。settings.is_live 等のプロパティで判定できます。
- J-Quants API はレート制限があるため jquants_client は内部でスロットリングとリトライを実装しています。テストで高頻度に叩かないでください。
- DuckDB スキーマは init_schema() が冪等に作成します。既存データを消さずに拡張できます。
- ニュース収集は外部ネットワークに依存するため、SSRF/大小攻撃対策を行った実装になっていますが、運用時はソースの管理（ホワイトリスト）を行ってください。
- strategy 層（build_features, generate_signals）は execution 層（実際の発注）に依存しないよう設計されています。実際の発注は execution 層を実装して連携してください。

---

## 貢献 / 拡張案

- execution 層のブローカー（kabuステーション等）接続の具体実装
- モニタリング / アラート（Slack 通知）への統合
- AI スコア生成パイプライン（ai_scores テーブルの計算）
- テストケース・CI の整備（ユニット・統合テスト）
- requirements.txt / pyproject.toml の整備とパッケージ化

---

この README は現在のコードベースに基づいて作成しています。細部の挙動や追加の設定はソースコード（特に kabusys.config, kabusys.data.schema, kabusys.data.pipeline, kabusys.strategy）を参照してください。質問やドキュメント追加の要望があれば教えてください。