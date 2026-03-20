# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
市場データの取得・ETL、特徴量生成、シグナル算出、ニュース収集、DuckDB ベースのスキーマ管理などを含む一連の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを想定した内部ライブラリです。

- Data 層: J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、DuckDB スキーマ定義・初期化、ETL パイプライン
- Research 層: ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ（IC, forward returns 等）
- Strategy 層: 正規化済み特徴量から最終スコアを算出し、BUY/SELL シグナルを生成
- Execution 層: 発注・約定・ポジション管理のためのスキーマ（発注処理は別途実装を想定）

設計上のポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / DO UPDATE を利用）
- ネットワーク・API 呼び出しはリトライやレート制御を実装
- DuckDB をデータベースとして利用（オフラインでも利用可能）

---

## 主な機能一覧

- DuckDB スキーマ定義・初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（取得・保存: daily quotes / financials / market calendar）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl を用いた日次 ETL
- ニュース収集（RSS -> raw_news，記事ID 正規化・SSRF 対策）
- ファクター計算（momentum / volatility / value）
- 特徴量作成（クロスセクション Z スコア正規化・クリップ・features テーブルへの UPSERT）
- シグナル生成（重み付け合算による final_score、Bear レジーム判定、BUY/SELL の出力）
- カレンダー管理（営業日判定 / next_trading_day / get_trading_days 等）
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## 要求環境

- Python 3.10 以上（型ヒントの union 表記 (A | B) を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
# プロジェクトをパッケージとして管理している場合:
# pip install -e .
```

（実際の requirements.txt や pyproject.toml がある場合はそれに従ってください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。プロジェクトルートは `.git` または `pyproject.toml` を起点に判定します。自動読み込みを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意 / デフォルト付き:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

設定アクセス:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

環境変数が必須で未設定の場合、Settings プロパティは ValueError を投げます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # 必要に応じてその他パッケージを追加
   ```

3. .env ファイルを準備（.env.example を参考に）
   - JQUANTS_REFRESH_TOKEN 等の必須値を設定

4. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   init_schema はデータディレクトリが無ければ自動作成します。

---

## 使い方（代表的な例）

- DuckDB 接続の取得 / 初期化
```python
from kabusys.data.schema import init_schema, get_connection

# 初期化（ファイルがなければ作成）
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続のみ行う場合
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 の差分取得・保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（features テーブルへの保存）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの保存）
```python
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, target_date=date(2024, 1, 1))
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS から raw_news / news_symbols へ）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes はニュース本文から抽出する有効銘柄コードの集合
known_codes = {"7203", "6758"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数, ...}
```

- 直接 J-Quants API を呼ぶ（認証・ページネーション・保存はクライアントが処理）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

---

## よく使うモジュール一覧

- kabusys.config — 環境変数 / 設定管理
- kabusys.data.schema — DuckDB スキーマ定義・初期化
- kabusys.data.jquants_client — J-Quants API クライアント・保存関数
- kabusys.data.pipeline — ETL の実装（run_daily_etl 等）
- kabusys.data.news_collector — RSS ニュース収集、記事正規化、銘柄抽出
- kabusys.data.calendar_management — 市場カレンダー関連ユーティリティ
- kabusys.data.stats — zscore_normalize 等
- kabusys.research.* — ファクター計算・解析ユーティリティ
- kabusys.strategy.feature_engineering — features テーブル生成（build_features）
- kabusys.strategy.signal_generator — signals 生成（generate_signals）

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - execution/  (発注関連の空モジュール等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py

（上記は主要ファイルの抜粋です。詳細はリポジトリ全体を参照してください。）

---

## 注意事項 / トラブルシュート

- Python バージョン: 3.10 以上を推奨（型記法に依存）
- 環境変数が不足していると起動時に例外が発生します（Settings._require で ValueError）
- J-Quants API の利用には有効なリフレッシュトークンが必要
- DuckDB ファイルのバックアップ・ロックに注意（複数プロセスが同時に書き込む場合は排他設計を検討）
- RSS フィードの取得では SSRF 対策・レスポンスサイズ制限を実装しています。取得できない場合はログを確認してください
- テストや CI で自動環境変数ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

---

## 今後の拡張案（参考）

- Execution 層の実装（ブローカー接続、オーダー送信の実装）
- モニタリング / Alerting（Slack 通知の統合）
- バッチスケジューラ（cron / Airflow など）向けのラッパー
- AI スコア生成パイプラインの実装（ai_scores テーブルへの保存）

---

ライセンスや貢献方法などのメタ情報はリポジトリのルートに LICENSE / CONTRIBUTING を置いて管理してください。README の改善要望や追加で載せたい利用例があれば教えてください。