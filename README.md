# KabuSys

日本株向け自動売買プラットフォームの構成要素ライブラリです。データ取得（J-Quants）、ETL／スキーマ管理、ファクター計算・特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの主要機能をモジュール化して提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

## プロジェクト概要

KabuSys は以下の目的で設計されたPythonモジュール群です。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存
- 生データ → 整形済みデータ → 戦略用特徴量 → シグナルの生成というデータレイヤードアーキテクチャ
- 研究（research）コードで算出した生ファクターを正規化して戦略用特徴量にする機能
- 特徴量と AI スコアを統合した最終スコアに基づく売買シグナルの生成
- RSS ベースのニュース収集と銘柄紐付け
- ジョブ（ETL / カレンダー更新 / ニュース収集 等）のためのユーティリティ
- 発注・約定・監査用のスキーマ設計（execution / audit）

設計方針として、Look-ahead バイアスの回避、冪等性（ON CONFLICT）、外部依存の最小化（可能な限り標準ライブラリ）を重視しています。

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ、ページネーション）
  - schema: DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline: ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - calendar_management: 市場カレンダーの判定・取得・更新ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン・IC・ファクターサマリー等の分析ユーティリティ
- strategy
  - feature_engineering.build_features: raw factor を統合・Zスコア正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成して signals テーブルへ保存
- config
  - 環境変数から設定を読み込む Settings（自動でプロジェクトルートの `.env` / `.env.local` を読み込み）
- audit / execution / monitoring
  - 発注・約定・監査関連のスキーマ定義とユーティリティ（スキーマは schema.init_schema で作成されます）

## 必要条件（依存パッケージ）

- Python 3.10+
- duckdb
- defusedxml

（プロジェクトで追加の依存が必要な場合は setup / requirements を参照してください。上記はコード中で明示的に利用されている主要ライブラリです。）

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   bash
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）。

   - pip install duckdb defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

3. 環境変数を設定します。プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効化されます）。

必須の環境変数（Settings に基づく）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意（デフォルト値あり）

- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...), デフォルト "INFO"

例 .env（プロジェクトルート）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

## 使い方（簡単な例）

以下は Python スクリプトや対話環境で使う際の典型的なワークフロー例です。

1. DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行して株価・財務・カレンダーを取得する

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 研究モジュールで得たファクターを正規化して features を作成する（target_date を指定）

```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナルを生成して signals テーブルへ保存する

```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

5. ニュース収集ジョブ（RSS）を実行する

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効なコードのセット（例: all codes from prices table）
known_codes = {"7203", "6758", "9984", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6. カレンダー更新ジョブを定期実行する（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- J-Quants API 呼び出しはレート制限（120 req/min）に従います。jquants_client は内部でスロットリングとリトライを行います。
- run_daily_etl や各 ETL 関数は内部で例外をキャッチして処理を続行する設計ですが、エラーは ETLResult.errors / logger に記録されます。
- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動ロードします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

## 重要な設計ルールと注意事項

- ルックアヘッドバイアスの防止: 戦略・特徴量計算はすべて target_date 時点までのデータのみを使用するように実装されています。
- 冪等性: API で取得した生データの保存は ON CONFLICT / DO UPDATE、あるいは INSERT ... DO NOTHING を使い、再実行に耐える設計です。
- トランザクション: 複数行挿入や置換はトランザクションで包まれており、原子性を保証します。失敗時は ROLLBACK を行います。
- セキュリティ: news_collector では SSRF 対策、XML パースに defusedxml を利用するなど安全性に配慮しています。
- ログと監査: audit モジュールは signal → order_request → execution の一連をトレースするスキーマを提供します。監査ログは削除しない前提で設計されています。

## ディレクトリ構成

主要ファイル/ディレクトリ（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         — RSS ニュース収集・前処理・DB保存
    - schema.py                 — DuckDB スキーマ定義・初期化 (init_schema)
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py    — 市場カレンダー判定／更新ジョブ
    - audit.py                  — 監査ログ（signal_events, order_requests, executions など）
    - features.py               — data.stats の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py        — momentum / volatility / value のファクター計算
    - feature_exploration.py    — IC / forward returns / summary 等の研究ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features（正規化・フィルタ等）
    - signal_generator.py       — generate_signals（最終スコア計算・BUY/SELL 生成）
  - execution/                   — 発注・執行関連（スケルトン）
  - monitoring/                  — 監視・メトリクス（スケルトン）
  - その他モジュール

（上記はコードベースから抽出した主要モジュール一覧です。実際のリポジトリでは追加のヘルパーやテスト等が含まれる可能性があります）

## 開発者向けメモ

- Settings（kabusys.config.Settings）は必要な環境変数をプロパティとして提供します。未設定の必須変数にアクセスすると ValueError が発生します。
- テスト時にプロジェクトルート検出や .env 自動ロードが干渉する場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 初期化: schema.init_schema(db_path) は parent ディレクトリを自動で作成します。インメモリ DB は `":memory:"` を渡せます。
- jquants_client のトークンはモジュールキャッシュで共有され、get_id_token() を呼ぶことで自動更新が行われます。

---

必要であれば、README に次の情報を追加できます:
- 詳細な API リファレンス（各関数の引数/戻り値の例）
- 実運用（paper_trading / live）時のデプロイ手順
- サンプル CI/cron ジョブ設定（ETL / calendar_update / news_collection の定期実行）
- テスト手順とモックの使い方

加筆希望があればどのセクションを詳述するか教えてください。