# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（部分実装）。  
データ収集（J‑Quants）→ ETL → 特徴量生成 → シグナル生成 → 実行／監視、という典型的なデータパイプラインと戦略層のユーティリティ群を提供します。

注意: このリポジトリはフル実装の一部を切り出したものであり、実運用には追加の実装（ブローカ接続、ジョブスケジューリング、監視・運用手順等）が必要です。

## 主な特徴

- データ取得
  - J‑Quants API クライアント（株価日足、財務諸表、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDは正規化 URL の SHA‑256）
- ETL / データ基盤
  - DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 差分 ETL（バックフィル対応、カレンダー先読み、品質チェック呼び出し）
  - 市場カレンダー管理（営業日/前後営業日/期間の営業日取得）
- 特徴量・リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクションの Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 戦略
  - 特徴量作成（build_features）: 研究で算出した生ファクターを正規化・合成して features テーブルへ UPSERT
  - シグナル生成（generate_signals）: features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ保存。Bear レジーム抑制、エグジット（ストップロス等）判定を実装
- セキュリティ・信頼性設計
  - API レート制御・リトライ・トークン自動リフレッシュ（J‑Quants）
  - RSS の XML パースに defusedxml、レスポンスサイズ制限、SSRF対策等
  - DuckDB 側は冪等性を意識した INSERT / ON CONFLICT 文を多用

## 必要条件

- Python 3.10 以上（Union 型の表記などに依存）
- 必須パッケージ（代表例）
  - duckdb
  - defusedxml

（pip 用の requirements.txt は同梱されていません。用途に応じて仮想環境を作成し必要なパッケージをインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install "duckdb>=0.6" defusedxml
```

## 環境変数（主なもの）

KabuSys は .env ファイルまたは環境変数から設定を読み込みます（自動ロードはプロジェクトルートに `.git` または `pyproject.toml` が存在する場合に有効）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot Token
- SLACK_CHANNEL_ID      : Slack 通知先 Channel ID

オプション（デフォルト値あり／説明）:
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する（1）
- KABUSYS による DB パス:
  - DUCKDB_PATH         : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH         : 監視用 SQLite 等（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

例 .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（開発環境）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに配置）
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

コマンド一行例:
```
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

## 使い方（代表的なワークフロー）

以下はライブラリの代表的な呼び出し例です。実運用ではジョブスケジューラ（cron / Airflow / Prefect 等）や監視を組み合わせてください。

1) 日次 ETL を実行してデータを取得・保存・品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初回: スキーマ初期化（既に初期化済みならスキップ可）
conn = init_schema("data/kabusys.duckdb")

# 日次ETL（target_date 省略で今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（features テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, date.today())
print("upserted features:", n)
```

3) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, date.today())
print("signals written:", n)
```

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄抽出）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コード集合（抽出に使用）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) カレンダーバッチ更新
```python
from kabusys.data.calendar_management import calendar_update_job
conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

## 推奨ワークフロー（運用例）

- 夜間バッチ（ETL・カレンダー更新・ニュース収集）を実行してデータを最新化
- 早朝に build_features → generate_signals を実行して当日シグナルを作成
- リスク管理・発注レイヤーで signals テーブルを読み取り、ブローカに発注
- 発注・約定情報を audit / executions テーブルでトレース
- Slack 通知やメトリクス収集で監視

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義 & init_schema()
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理
    - features.py             — data.stats の再エクスポート
    - audit.py                — 発注〜約定の監査テーブル定義（初期化）
    - (その他: quality.py などの品質チェックモジュール想定)
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py     — generate_signals（final_score, BUY/SELL 判定）
  - execution/                — 発注実装層（プレースホルダ）
  - monitoring/               — 監視/メトリクス（プレースホルダ）
- pyproject.toml, README.md 等（環境によって存在）

※ 上記は本コードベースで定義されている主要モジュールです。実際のリポジトリではさらにユーティリティやテストが含まれることがあります。

## 開発上の注意点

- DuckDB をデータ永続化に使用しています。並列アクセスやバックアップ戦略は運用次第で検討してください。
- J‑Quants API はレートリミットとトークン管理が必要です。実行環境でのトークン保護に留意してください。
- RSS フィード取得にはネットワークの外部依存およびセキュリティリスク（SSRF 等）があります。実装では防御策を講じていますが、運用側でもホワイトリスト管理などの追加対策を推奨します。
- generate_signals や build_features はルックアヘッドバイアス回避設計になっていますが、ETL の順序や target_date の扱いに注意して運用してください。

## 貢献・拡張案

- ブローカ接続（execution 層）の実装（kabuステーション等）
- ポートフォリオ最適化／リスク管理プラグイン
- Web UI やダッシュボード（監視・手動オーバーライド用）
- テストスイートの追加（単体テスト・統合テスト・モックによる外部 API テスト）

---

ライセンスやさらに詳しい設計ドキュメント（StrategyModel.md / DataPlatform.md / Research/）は別添の仕様書を参照してください。README の内容や使い方で不明点があれば教えてください。追加で導入コマンド例やサンプルスクリプトを用意します。