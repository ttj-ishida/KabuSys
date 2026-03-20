# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査・スキーマ管理などを含む内部モジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下のレイヤーを備えた日本株のアルゴリズム取引向け基盤ライブラリです。

- Data (ETL): J-Quants からの株価/財務/カレンダー取得、DuckDB への保存、品質チェック、ニュース収集
- Research: ファクター計算（モメンタム / ボラティリティ / バリュー）・探索用ユーティリティ（IC・将来リターン）
- Strategy: 特徴量合成（正規化）とシグナル生成（BUY/SELL 判定）
- Execution / Monitoring: 発注・約定・ポジション・監査のためのスキーマとユーティリティ（実装のベース）

設計上の特徴:
- DuckDB ベースのローカルデータストア（冪等な保存ロジック）
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみを使用）
- API 呼び出しに対するレート制御・リトライ・トークンリフレッシュを実装
- ニュース収集での SSRF / XML Bomb 等のセキュリティ対策

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env ファイル / 環境変数の自動読み込み（プロジェクトルート基準）
  - settings オブジェクトで設定値を取得（J-Quants トークン、kabu API パスワード、Slack トークン等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページネーション・保存関数）
  - schema: DuckDB スキーマ定義と初期化（各レイヤーのテーブルとインデックス）
  - pipeline: 日次 ETL（calendar / prices / financials）と品質チェック、差分取得ロジック
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns, calc_ic, factor_summary 等の探索ツール
- kabusys.strategy
  - build_features: 生ファクターを正規化して features テーブルへ UPSERT
  - generate_signals: features + ai_scores を統合して BUY/SELL シグナルを作成
- kabusys.execution / monitoring (パッケージ化済み、発注や監査に関連するスキーマ・プレースホルダあり)

---

## セットアップ手順

必要なソフトウェア:
- Python 3.8+（コードの型記述は 3.10 風ですが、3.8+ 想定）
- DuckDB（Python パッケージとしてインストール）
- defusedxml（RSS パーサ保護のため）
- その他標準ライブラリ

推奨インストール例:

1. リポジトリをクローンして開発環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # 開発時にパッケージ化して使う場合
   pip install -e .
   ```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルト値あり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...，デフォルト INFO）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml が見つかるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。

例: `.env`（レポジトリに含めないでください）
```
JQUANTS_REFRESH_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は最小限のワークフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルトのパス（settings からも取得可能）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から株価・財務・カレンダーを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

# conn は init_schema が返す接続
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量を作成（feature テーブルへ保存）
```python
from kabusys.strategy import build_features
from datetime import date

cnt = build_features(conn, target_date=date.today())
print(f"features upserted: {cnt}")
```

4) シグナル生成（features と ai_scores を参照して signals に書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, target_date=date.today())
print(f"total signals: {total_signals}")
```

5) ニュース収集ジョブ（RSS から raw_news に保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は抽出対象となる有効銘柄コードの集合（例: set(["7203","6758",...])）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}
```

補足:
- ETL や各処理は冪等に設計されています（target_date 単位で DELETE → INSERT の置換を行うため再実行が安全）。
- generate_signals は weights / threshold を引数で上書き可能です。

---

## 環境設定 & 実運用注意点

- KABUSYS_ENV は次のいずれか: "development", "paper_trading", "live"。運用に合わせて適切に設定してください（is_live / is_paper / is_dev で判定可能）。
- ロギングレベルは LOG_LEVEL で制御します。運用では INFO か WARNING、デバッグ時は DEBUG。
- J-Quants API のレート制限（120 req/min）を尊重するためクライアントは内部でスロットリングを行います。
- ニュース収集では外部 URL のリダイレクトやプライベートアドレスへのアクセスをブロックする等の安全対策があります。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。必要に応じてバックアップを取ってください。
- メインの ETL と calendar 更新ジョブはスケジューラ（cron / Airflow 等）で夜間に実行する想定です。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - schema.py              — DuckDB スキーマ定義・init_schema
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS ニュース取得・保存・銘柄抽出
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - features.py            — features 用ユーティリティの再エクスポート
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - audit.py               — 監査ログ用スキーマ DDL
    - pipeline_quality (参照モジュール) — 品質チェック用機能（quality モジュールは pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — IC / 将来リターン / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features
    - signal_generator.py    — generate_signals
  - execution/               — 発注・約定・ポジションに関するパッケージ（entry points）
  - monitoring/              — 監視・メトリクス関連（sqlite 等）

（各モジュールの詳細はソースコードの docstring を参照してください）

---

## 開発・テスト

- 単体テストや CI を導入する場合、環境変数の自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト専用の環境を用意してください。
- DB の初期化に `:memory:` を渡すとインメモリ DuckDB が使えます（単体テストで便利です）。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

---

## ライセンス・貢献

- 本リポジトリのライセンスやコントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はメンテナに問い合わせてください）。

---

必要であれば、README に以下を追加できます:
- 例となる cron / systemd タイマーの設定例
- ETL / calendar / news のサンプル CLI スクリプト
- Slack 通知の使用例
- よくあるトラブルシューティング（API トークンエラー、DuckDB 権限、ネットワークエラー等）

追加希望があれば教えてください。