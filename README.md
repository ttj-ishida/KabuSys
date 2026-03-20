# KabuSys

日本株向けの自動売買基盤（データ収集・加工・特徴量生成・シグナリング・監査／実行レイヤ）を提供するライブラリ群です。DuckDB を内部データベースとして利用し、J-Quants API や RSS などからデータを収集・保存、研究（research）→ 戦略（strategy）→ 実行（execution）へとつなぐことを想定しています。

---

## 主要な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ニュース収集（正規化・前処理・銘柄抽出）
  - DuckDB への冪等的な保存（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- ETL パイプライン
  - 差分取得（最終取得日からの差分、自動バックフィル）
  - カレンダー先読み・品質チェック（欠損・スパイク等の検出）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value など）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ
  - Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量エンジニアリング（ユニバースフィルタ・Z スコア正規化・クリップ）
  - シグナル生成（複数コンポーネントのスコア統合・Buy / Sell 判定・Bear レジーム抑制）
- 実行・監査（execution / audit）
  - 信号テーブル・発注キュー・注文・約定・ポジション・監査ログ用スキーマ
- カレンダー管理（営業日判定・next/prev_trading_day 等）
- セキュリティ・堅牢性対策
  - RSS の SSRF 対策・XML パースの防御（defusedxml）
  - API レート制御・リトライ（指数バックオフ・トークンリフレッシュ）

---

## 動作要件

- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml
- OS: 特に制約なし（Linux / macOS / Windows）

※要件はプロジェクトの実際の setup / pyproject.toml / requirements.txt に合わせて調整してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトの requirements ファイルがあればそれを利用）

4. 環境変数を設定
   - ルートに `.env` / `.env.local` を置くと自動的に読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（少なくともこれらは設定する必要があります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（execution 関連で使用）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意・デフォルトあり:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマを作成するユーティリティが提供されています。初期化例:

Python 例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
```

init_schema は必要なテーブル（raw / processed / feature / execution / audit 等）とインデックスをすべて作成します（冪等）。

---

## 使い方（主要 API）

以下は代表的な操作のサンプルです。実運用ではログ設定や例外ハンドリング、スケジュール（cron / CI / Airflow 等）を追加してください。

- 日次 ETL（株価・財務・カレンダー取得＋品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（strategy 層）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals inserted: {total_signals}")
```

- ニュース収集ジョブ（RSS から raw_news を保存）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う銘柄コード集合（文字列の4桁コード）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar entries saved: {saved}")
```

- J-Quants からのデータ取得（クライアントの使用例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys 以下を中心に説明します。パッケージは __init__ 等を含みます。

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、必須チェック、環境 / ログレベル等）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
    - news_collector.py — RSS フィード収集・前処理・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema, get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — market_calendar 管理・営業日関数・calendar_update_job
    - features.py — data 層の特徴量ユーティリティエクスポート
    - audit.py — 監査ログスキーマ（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ・rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py — final_score の計算と signals テーブル生成
  - execution/ — 発注・execution 層（空の __init__ がある想定）
  - monitoring/ — 監視関連（sqlite 等を使う想定）

（実際のリポジトリには追加のユーティリティ・ドキュメント・設定ファイルがある場合があります）

---

## 設定・運用上の注意

- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかを設定してください。live では実際の発注や通知などを行う想定です。
- J-Quants の API レート制限（デフォルト 120 req/min）を尊重する設計になっていますが、運用環境に応じた調整やモニタリングを行ってください。
- RSS 収集では外部から受け取るデータに対する安全対策（SSRF、XML Bomb、Content-Length チェック 等）を実装していますが、収集対象や環境に応じてさらに検討してください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップ・スナップショット運用を推奨します。
- ETL は各ステップごとに例外を捕捉して処理継続するため、ログ・監査を確認して問題を把握してください。
- 実運用での発注ロジック（execution 層）は別途 broker と連携する実装が必要です。本パッケージの戦略層はシグナル生成までを担当し、実際の発注は execution 層を介して行う設計方針です。

---

## 開発・拡張のヒント

- 単体テストやモックを使って外部 API 呼び出し（jquants_client._request や news_collector._urlopen 等）を差し替えるとテストが容易になります。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装になっていますが、分析やプロトタイピング時は pandas を使った別実装で比較すると便利です。
- features / signals のルール（閾値や重み）は generate_signals の引数で上書きできます。戦略のバックテストや A/B テストのためにパラメータ注入を活用してください。

---

この README は主要な使い方と設計意図の概要を記載しています。詳細な仕様（StrategyModel.md、DataPlatform.md、Research ドキュメント等）がプロジェクトに含まれている場合はそちらも参照してください。質問やドキュメント追加の希望があればお知らせください。