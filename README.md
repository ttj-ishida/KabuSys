# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量戦略に必要なデータ基盤と戦略レイヤーを提供する Python パッケージです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータベーススキーマの定義と永続化（冪等性重視）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ファクター計算（momentum/volatility/value 等）と Z スコア正規化
- 戦略用特徴量の構築とシグナル生成（BUY / SELL 判定ロジック）
- RSS からのニュース収集と銘柄紐付け（SSRF/サイズ制限など安全対策あり）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注／監査のためのスキーマ（監査ログ設計を含む）

設計方針としては、ルックアヘッドバイアスを避けるために「target_date 時点のデータのみを使用すること」、および外部 API（発注等）への直接依存を避けることが挙げられます。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存ユーティリティ）
  - schema: DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution 層）
  - pipeline: ETL（差分取得、保存、品質チェック）、日次 ETL エントリ
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー管理、営業日演算ユーティリティ
  - stats: Z スコア正規化など統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- config: .env / 環境変数管理（自動 .env 読み込み、必須チェック）
- execution, monitoring: 発注・監視用のプレースホルダモジュール（将来的な実装想定）
- audit: 監査ログ用スキーマ（signal_events / order_requests / executions 等）

主要な特長:
- DuckDB を用いたローカルでの高速分析と永続化
- 冪等性を考慮した DB 保存（ON CONFLICT 等）
- J-Quants API のレート制御および堅牢なリトライロジック
- RSS の SSRF 対策、コンテンツ正規化、銘柄抽出機能
- 戦略ロジックは発注層に依存せず、signals テーブルに出力することで後段と疎結合

---

## 要求環境 / インストール

- Python 3.10 以上（PEP 604 の union 型 `X | Y` を使用しているため）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

例（venv 使用）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージを開発インストールする場合（プロジェクトルートに pyproject.toml があることを想定）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## 環境変数（.env）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（CWD に依存しない探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（execution 関連で使用）
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（監視モジュール等で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡易の .env 例:

```env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージをインストールする（上記参照）
3. プロジェクトルートに `.env` を作成し、必須キーを設定する
4. DuckDB スキーマを初期化する

例:

```bash
# 仮想環境作成済み、依存インストール済みとする
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

このコマンドで必要なディレクトリが作成され、全テーブル・インデックスが作成されます。

---

## 使い方（主要ユースケース）

以下はライブラリを使った簡単な Python スニペット例です。実行前に .env を設定し、schema を初期化してください。

1) DuckDB 接続の取得

```python
from kabusys.data import schema
conn = schema.get_connection('data/kabusys.duckdb')
# 初回は init_schema を呼ぶこと
# conn = schema.init_schema('data/kabusys.duckdb')
```

2) 日次 ETL を実行（J-Quants からデータ取得して保存）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')  # 初期化して接続を得る
result = run_daily_etl(conn)  # target_date を指定しなければ今日の処理を実行
print(result.to_dict())
```

3) 特徴量（features）構築

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection('data/kabusys.duckdb')
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection('data/kabusys.duckdb')
signals_count = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {signals_count}")
```

5) ニュース収集ジョブ（RSS）を実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection('data/kabusys.duckdb')
# known_codes は銘柄抽出に使うコードセット（例: 上場銘柄コードのセット）
result = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
print(result)
```

6) カレンダー更新バッチ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection('data/kabusys.duckdb')
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- generate_signals / build_features は DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を前提とします。ETL を先に実行してください。
- J-Quants API 呼び出しには認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- ニュース収集や外部 URL 取得はネットワーク例外が発生する可能性があるため、呼び出し側で例外処理を行ってください。

---

## ディレクトリ構成

主要ファイル・モジュールの概観（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存ユーティリティ
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・正規化・保存・銘柄抽出
    - calendar_management.py — カレンダー更新 / 営業日ユーティリティ
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ関連 DDL（signal_events / order_requests / executions）
    - quality.py?            — （品質チェック関連モジュール: pipeline 参照。存在する場合）
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value 計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル生成
    - signal_generator.py    — BUY/SELL シグナル生成
  - execution/               — 発注層プレースホルダ
  - monitoring/              — 監視プレースホルダ

（実際のファイルはコードベースに合わせてご確認ください）

---

## 開発・テスト

- 開発中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env 読み込みを無効化できます（ユニットテスト等で便利）。
- 各モジュールは外部通信部分を抽象化しているため、ネットワーク呼び出し（jquants_client._request や news_collector._urlopen など）をモックしてユニットテストできます。
- DuckDB のインメモリ DB（":memory:"）を使うことでテストの高速化が可能です。

---

## 注意事項 / 今後の拡張

- execution / monitoring モジュールは将来的な発注実装・監視ロジックを想定したプレースホルダです。実運用で証券会社 API を呼ぶ際は追加実装と十分なテストが必要です。
- AI スコアやニュース解析のモデルは外部で作成・投入する前提です（ai_scores テーブルを経由）。
- 実運用での live 環境使用時は KABUSYS_ENV=live を設定し、十分なリスク管理・ログ監査を実施してください。
- カレンダーや価格データの信頼性、データ欠損時の挙動については品質チェックを有効にして監視してください。

---

README に関するフィードバックや補足してほしい使用例があれば教えてください。ファイル例や具体的なスクリプト（cron / systemd ジョブ例）も追加できます。