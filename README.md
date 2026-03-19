# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants や RSS、kabuステーション 等からデータを取得・蓄積し、研究用ファクター計算、特徴量の正規化、シグナル生成、ETL・カレンダ管理・ニュース収集、監査ログ等をサポートします。

--- 

## 特徴（概要）
- DuckDB を用いたローカルデータベース設計（Raw / Processed / Feature / Execution レイヤー）
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- ETL パイプライン（差分取得、バックフィル、品質チェックとの連携）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ、日次UPSERT）
- シグナル生成（ファクター + AI スコアを統合して BUY/SELL を生成）
- RSS ベースのニュース収集（SSRF 対策、トラッキング除去、銘柄抽出）
- 監査ログ（signal → order → execution を UUID でトレース）
- テスト容易性に配慮した設定・モジュール分離

---

## 主な機能一覧
- data/
  - jquants_client: J-Quants からの株価 / 財務 / カレンダー取得と DuckDB 保存（冪等）
  - pipeline: ETL ジョブ（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - schema: DuckDB スキーマ初期化（init_schema, get_connection）
  - news_collector: RSS 取得と raw_news / news_symbols の保存（SSRF/サイズ/XML安全性対策）
  - calendar_management: 営業日判定、next/prev_trading_day 等
  - features / stats: Z スコア等の統計ユーティリティ
  - audit: 監査ログ用テーブル定義
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリー
- strategy/
  - feature_engineering: ファクター合成・ユニバースフィルタ・正規化 -> features テーブルへ保存
  - signal_generator: final_score 計算、BUY/SELL 判定、signals テーブルへ保存
- config:
  - 環境変数/設定管理（.env/.env.local 自動ロード、必須チェック、環境モード判定）

---

## 必要環境
- Python 3.10 以上（型ヒントの union 演算子等を使用）
- ランタイム依存ライブラリ（最低限）:
  - duckdb
  - defusedxml
- （外部連携）J-Quants API、Slack、kabuステーション の利用にはそれぞれの認証情報が必要

例（最低インストール）:
```sh
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトの実行に必要な追加パッケージがある場合は適宜追加してください。

---

## 環境変数 / 設定
自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、`.env` → `.env.local` の順にロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

主に使用される環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — 通知対象チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定は以下のようにアクセスできます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（ローカルでの初期化例）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. プロジェクトルートに `.env`（または `.env.local`）を用意し、必要な環境変数を設定
   - .env.example があれば参考に作成してください
5. DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要な利用例）

- 日次 ETL（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（features テーブルの更新）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルの更新）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS から raw_news 保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)  # {source_name: saved_count}
```

- J-Quants から取得して保存（個別利用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema(settings.duckdb_path)
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} price records")
```

---

## ワークフロー（例）
典型的な夜間バッチの流れ:
1. calendar_update_job（market_calendar を先に更新）
2. run_daily_etl（株価・財務の差分取得、品質チェック）
3. build_features（features テーブルの更新）
4. generate_signals（signals を生成）
5. signal_queue / execution 層で発注 → orders / executions / positions を記録
6. audit テーブルにトレース情報を記録

---

## テスト・デバッグのポイント
- 環境変数自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- DuckDB のテストは `:memory:` を使ってメモリ DB で行えます:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```
- 外部 API 呼び出し（ネットワーク）を切り離した単体テストは、jquants_client や news_collector のネットワーク関数をモックしてください

---

## ディレクトリ構成
（主要ファイル / モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - stats.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - (その他 data 関連モジュール)
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
      - (発注実行関連モジュール: broker アダプタ等を配置予定)
    - monitoring/
      - (監視・アラート関連モジュール)
- pyproject.toml / setup.cfg / .gitignore など（プロジェクトルート）

---

## 注意事項 / 設計上の留意点
- 多くの操作は DuckDB のテーブル存在やデータ整合性に依存します。初回は `init_schema()` を必ず実行してください。
- J-Quants API のレート制限やレスポンス時間に注意（jquants_client でレート制御・リトライ実装済み）。
- システムは「ルックアヘッドバイアス」対策を設計方針に組み込んでいます：target_date 時点までのデータのみを用いる、fetched_at を保存して取得時点をトレース可能にする等。
- production（live）運用時は env=live に設定し、Slack や kabuステーションとの連携を慎重にテストしてください（paper_trading 環境での検証推奨）。

---

## 貢献・拡張
- 新しいデータソースやブローカーの実装は `data/` や `execution/` 下にプラグイン形式で追加できます。
- 監査（audit）層や監視（monitoring）を拡張して運用の可観測性を高めてください。

---

README で不足している具体的な導入手順（依存パッケージ一覧、CI設定、運用 runbook など）が必要であれば、追加情報を教えてください。さらに詳しい使用例（cron/batch スクリプト、Slack 通知サンプル、kabuステーション連携例）も作成できます。