# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。データ取得（J-Quants）、ETL、DuckDB スキーマ、ファクター計算・特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略実行に必要な主要コンポーネントを提供します。設計は「ルックアヘッドバイアス回避」「冪等性」「堅牢なエラーハンドリング」を重視しています。

---

## 主な機能

- データ取得
  - J-Quants API クライアント（rate limiter、リトライ、トークン自動リフレッシュ、ページネーション）
  - 株価日足 / 財務データ / 市場カレンダーの取得・DuckDB への冪等保存
- データ基盤
  - DuckDB ベースのスキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（日次差分取得、バックフィル、品質チェック支援）
- リサーチ（研究）機能
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算・IC（Spearman）・ファクター統計サマリ
- 特徴量エンジニアリング
  - 生ファクターの結合・ユニバースフィルタ・Zスコア正規化・クリッピング
- シグナル生成
  - 正規化済み特徴量＋AIスコアを統合して final_score を算出
  - Bear レジーム判定、BUY/SELL の生成・冪等保存
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、サイズ制限、XML セーフパース）
  - 記事正規化・ID生成・raw_news への冪等保存・銘柄抽出と紐付け
- マーケットカレンダー管理（営業日判定、次/前営業日の算出）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）

---

## 必要条件

- Python 3.10 以上（型アノテーションに PEP 604 等の構文を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

インストール例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをソース配布として扱う場合
pip install -e .
```

※プロジェクトに requirements ファイルがある場合はそれを使用してください。

---

## 環境変数 / .env

KabuSys はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動的に読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings から参照されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack Bot Token
- SLACK_CHANNEL_ID      : Slack チャンネル ID

その他（任意）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

サンプル `.env`（例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（要約）

1. Python 仮想環境を作成して有効化
2. 依存ライブラリをインストール（duckdb, defusedxml 等）
3. 必須環境変数を `.env` に設定（またはCI/OS 環境変数に設定）
4. DuckDB スキーマを初期化
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
5. ETL / 特徴量計算 / シグナル生成 を実行

---

## 使い方（主要な API と実行例）

以下は典型的なワークフローの例です。すべての操作は Python スクリプト内で実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量作成（features テーブルに書き込む）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date.today())
print("features upserted:", count)
```

4) シグナル生成（signals テーブルに書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, date.today(), threshold=0.6)
print("signals generated:", total)
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes = set([...])  # 銘柄コードの集合を渡すと記事に紐付けて保存する
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

7) J-Quants 低レベルクライアント（必要に応じて直接使用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date.today())
saved = save_daily_quotes(conn, records)
```

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ベースのニュース収集・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・更新ジョブ
    - audit.py — 監査ログ用の DDL と初期化補助
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター結合・ユニバースフィルタ・正規化→features テーブル書き込み
    - signal_generator.py — final_score 計算・BUY/SELL 判定・signals テーブル書き込み
  - execution/ (空のパッケージプレースホルダ)
  - monitoring/ (パッケージプレースホルダ)

---

## 設計上の注意点 / 補足

- 冪等性
  - DuckDB への保存は可能な限り ON CONFLICT / INSERT ... DO UPDATE / INSERT ... DO NOTHING を使い冪等に実装されています。
- ルックアヘッドバイアス対策
  - 特徴量作成・シグナル生成では target_date 時点までのデータのみを使用する設計です。
- 環境変数自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` → `.env.local` の順で読み込みを行います（OS 環境変数優先）。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- レート制限・リトライ
  - J-Quants クライアントは 120 req/min の制限に合わせたスロットリングと、HTTP 408/429/5xx に対する指数バックオフを実装しています。401 はトークン自動更新を試みます。

---

## 参考 / 開発メモ

- テストや運用での利用時は `KABUSYS_ENV` を `paper_trading` に設定し、実取引を避けるなどの運用ルールを推奨します。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に作成されます。必要に応じて `DUCKDB_PATH` を設定してください。
- Slack 通知などは設定されたトークンを用いて外部に通知できる仕組みを想定しています（実装は別途）。

---

この README はソースコードの主要な API とワークフローを簡潔にまとめたものです。実運用前に DataPlatform.md / StrategyModel.md 等の設計ドキュメント（ソースのコメントに参照あり）を確認し、環境設定やリスク管理ポリシーを整備してください。