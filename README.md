# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買（データプラットフォーム + 戦略）ライブラリです。J-Quants API から市場データ・財務データ・マーケットカレンダー・ニュースを取得して DuckDB に保存し、特徴量生成・シグナル生成・実行フロー（発注・約定・ポジション管理）に至る一連の処理を提供します。

主な目的
- データ取得（J-Quants）→ DuckDB に蓄積（冪等）
- 研究（research）向けファクター算出と特徴量正規化
- 戦略（strategy）によるシグナル生成（BUY / SELL）
- 実行レイヤ（execution）・監査ログ連携のためのスキーマ設計
- ニュース収集と銘柄紐付け

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 必須環境変数の取得・検証ロジック

- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、レート制御）
  - raw / processed / feature / execution 層の DuckDB スキーマと初期化
  - ETL パイプライン（run_daily_etl、差分取得、バックフィル、品質チェック連携）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS パーサ、安全対策（SSRF、XML爆弾、サイズ制限）、銘柄抽出）
  - 統計ユーティリティ（Z スコア正規化 等）

- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターサマリー

- 戦略モジュール（kabusys.strategy）
  - 特徴量作成（build_features）：研究で算出した raw factor を統合・正規化して features テーブルへ保存
  - シグナル生成（generate_signals）：features と ai_scores を組み合わせて final_score を算出し signals テーブルへ保存
  - Bear レジーム抑制、STOP-LOSS 等のエグジット判定実装

- 監査（kabusys.data.audit）
  - シグナル → 発注 → 約定 のトレーサビリティ用テーブル群（冪等・監査ログ）

---

## セットアップ

前提
- Python 3.9+（コードは typing の | 型注釈等を使用）
- DuckDB を利用するため、Python 環境に duckdb パッケージが必要
- RSS パース時に defusedxml を使用

例: 仮想環境の作成と依存インストール（プロジェクトルートで実行）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（パッケージが setup 配置されている前提）
pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

オプション（デフォルト値あり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

.env 例（プロジェクトルートに配置）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env 読み込みについて
- パッケージはプロジェクトルート（.git または pyproject.toml のある階層）を探索して .env / .env.local を自動読み込みします。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

---

## 初期化・使い方（基本例）

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path で指定された DB を初期化
conn = schema.init_schema(settings.duckdb_path)
```

- ":memory:" を渡すとインメモリ DB になります。

2) 日次 ETL 実行（データ取得 → 保存 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
print(result.to_dict())
```

3) マーケットカレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

4) ニュース収集（RSS）と保存（既知銘柄コードセットを渡すと銘柄紐付けも実行）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) 特徴量作成（strategy 層）

```python
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, target_date=date(2024, 1, 31))
print("features upserted:", cnt)
```

6) シグナル生成

```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date(2024, 1, 31))
print("signals written:", total)
```

注意
- これらの関数は DuckDB のテーブル構造（prices_daily / raw_financials / features / ai_scores / positions 等）を前提としています。初回は schema.init_schema() を必ず実行してください。
- J-Quants クライアントは rate-limit（120 req/min）・リトライ・トークン自動リフレッシュ等の仕組みを備えています。

---

## 実運用についてのポイント

- 環境（KABUSYS_ENV）に応じて実行振る舞い（paper_trading / live）を切り替えることを想定しています。settings.is_live / is_paper / is_dev を参照して下さい。
- ETL は差分取得が基本です。バックフィル日数のパラメータにより最終取得日の数日前から再取得して後出し修正を吸収します。
- ニュース収集では SSRF・XML BOM・Gzip bomb 等に対する防御を組み込んでいます。
- DuckDB 側のテーブルは ON CONFLICT を使うなど冪等性を担保する設計です。
- シグナル→発注→約定の監査ログを保存するテーブル群を備え、UUID ベースのトレーサビリティを確保しています。

---

## ディレクトリ構成

プロジェクトは src レイアウトです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS 取得・前処理・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — カレンダー管理（営業日判定）
    - features.py                  — data.stats の再エクスポート
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ用テーブル定義
    - quality.py?                  — （品質チェックモジュール想定/参照される）
  - research/
    - __init__.py
    - factor_research.py           — momentum/volatility/value の計算
    - feature_exploration.py       — IC・将来リターン・サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブルへ正規化して保存
    - signal_generator.py          — final_score 計算・BUY/SELL シグナル生成
  - execution/                      — 発注/実行層（パッケージ化済み、実装は別ファイル）
  - monitoring/                     — 監視系（存在が示唆されているモジュール）

（この README はコードベースの抜粋に基づいて作成しています。実際のファイルはさらに存在する可能性があります。）

---

## テスト & 開発

- 自動 .env 読み込みをテスト中に無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB のインメモリ接続を使えば簡単にユニットテストが可能:
  - schema.init_schema(":memory:")

---

## ライセンス・貢献

この README はコードスニペットに基づく概要です。実際の LICENSE や貢献ガイドラインはリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）を参照してください。

---

不明点や README に追加したい使い方（例: 実際の cron 設定、Airflow/DAG 例、Slack 通知セットアップなど）があれば教えてください。必要に応じてサンプルジョブ定義や運用手順を追加します。