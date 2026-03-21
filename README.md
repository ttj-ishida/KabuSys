# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
DuckDB をデータストアとして使用し、J-Quants からの市場データ収集、ニュース収集、ファクター計算、特徴量生成、シグナル生成、ETL パイプライン、監査ログなどを含む設計になっています。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（主な設定）
- ディレクトリ構成
- 開発 / 運用上の注意

---

## プロジェクト概要
KabuSys は以下のレイヤーを備えたシステムを提供します。

- Raw layer: J-Quants など外部ソースから取得した生データ（株価・財務・ニュースなど）
- Processed layer: 日次価格やマーケットカレンダー等の整形済みデータ
- Feature layer: 戦略/AI 用の特徴量（normalized features, ai_scores 等）
- Execution layer: シグナル・発注・約定・ポジション・監査ログ

設計方針としては「ルックアヘッドバイアス防止」「冪等性（Idempotency）」「テストしやすさ」「外部 API や発注層への直接の副作用の分離」を意識しています。

---

## 機能一覧
主な機能（モジュール）:

- 環境設定
  - 自動 .env 読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で必須キー取得とバリデーション
- データ取得・保存（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得・バックフィル、品質チェック呼び出し、日次 ETL 実行
- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ作成 / 初期化（各レイヤーのテーブル定義、インデックス）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、前処理、raw_news への保存、銘柄コード抽出
  - SSRF / XML 攻撃対策、受信サイズ制限、記事 ID の冪等生成
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - IC / forward returns / 統計サマリ等
- 戦略モジュール（kabusys.strategy）
  - 特徴量構築（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクションの Z スコア正規化など
- 監査・実行周り（schema にテーブル定義、audit モジュール等）

---

## セットアップ手順

1. Python 環境（推奨: 3.9+）を用意します。
2. 仮想環境を作成して有効化します（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストールします（最低限）:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクトに requirements ファイルや pyproject があればそちらを利用してください。ネットワーク関連は標準ライブラリ urllib を使用しているため requests は必須ではありません）

4. 環境変数を設定します（下記「環境変数」参照）。開発ではルートに .env / .env.local を置くと自動で読み込まれます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマを初期化します（例）:
   - Python REPL で:
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")

   init_schema は必要な親ディレクトリを自動で作成し、全テーブル／インデックスを作成します。

---

## 使い方（簡易サンプル）

以下は基本的な操作例です。用途に応じて適宜ラップして運用してください。

- DB 初期化（1 回だけ）
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行（市場カレンダー・株価・財務を差分取得して保存、オプションで品質チェック）
```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- 特徴量構築
```
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"built {n} features")
```

- シグナル生成
```
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31))
print(f"inserted {count} signals")
```

- ニュース収集（RSS）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
import duckdb

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効銘柄コード集合
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

---

## 環境変数（主な設定）

以下はコードで参照される主要な環境変数です。必須のものは settings で _require() によって未設定時に例外が出ます。

必須（実運用で必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動で .env を読み込まない
- KABUSYS_API_BASE_URL: kabu の base URL（デフォルトはコード内のデフォルトを参照）
- DUCKDB_PATH: デフォルト DB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

注: プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）。必要に応じて .env.example を参考にしてください。

---

## ディレクトリ構成（主要ファイル）
（この README は与えられたコードベースを元にしています）

src/
  kabusys/
    __init__.py
    config.py                          # 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py                # J-Quants API クライアント + 保存
      news_collector.py                # RSS ニュース収集・保存
      schema.py                        # DuckDB スキーマ定義・初期化
      stats.py                         # 統計ユーティリティ（zscore 等）
      pipeline.py                      # ETL パイプライン（run_daily_etl 等）
      features.py                      # data.stats の再エクスポート
      calendar_management.py           # 市場カレンダー管理ユーティリティ
      audit.py                          # 監査ログ用 DDL（未完の箇所あり）
    research/
      __init__.py
      factor_research.py               # momentum/value/volatility の計算
      feature_exploration.py           # forward returns / IC / summary
    strategy/
      __init__.py
      feature_engineering.py           # features テーブル構築
      signal_generator.py              # final_score 計算と signals 生成
    execution/                          # 発注実行層（パッケージ存在）
    monitoring/                         # 監視・メトリクス（パッケージ存在）

（注）audit.py の末尾にインデックス定義の途中で切れている部分が見られます。実運用前にファイル末尾が完全であることを確認してください。

---

## 開発 / 運用上の注意

- 冪等性: データ保存は原則 ON CONFLICT（upsert）や INSERT ... ON CONFLICT DO NOTHING を利用して二重投入を防いでいます。
- ルックアヘッドバイアス: 特徴量・シグナル生成は target_date 時点のデータのみを使用するよう設計されています。
- レート制限 / リトライ: J-Quants クライアントは 120 req/min の固定間隔スロットリングと指数バックオフを備えています。401 はトークン自動リフレッシュ処理を行います。
- ニュース収集では XML 攻撃や SSRF を防ぐための対策を入れています（defusedxml, リダイレクト時のホスト検査、受信最大サイズ制限など）。
- market_calendar が未取得でも運用できるようフォールバック（曜日ベース）がありますが、正確な営業日判定のためにはカレンダーデータの取得を推奨します。
- ログレベルや環境（development/paper_trading/live）は settings から取得し厳密にチェックされます。値が不正な場合は例外を投げます。

---

## 貢献 / 拡張
- strategy、execution、monitoring 層は実運用の要件に合わせて実装・拡張してください（例: 実際の証券会社 API とのブリッジ、ポジション管理ルール、リスク制御）。
- テスト: id_token などを注入可能な設計なのでモックを使った単体テストが書きやすくなっています。CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト環境を制御してください。

---

必要であれば README にサンプル .env.example、起動スクリプト、より詳細な API 仕様（関数の引数や戻り値の詳細）や運用手順（cron ジョブ設定、ログローテーション、バックアップ方針）を追加します。どの情報を優先して追記するか指定してください。