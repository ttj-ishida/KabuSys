# KabuSys

日本株向けの自動売買／データプラットフォーム用 Python ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、特徴量計算、監査ログなどを備え、戦略実験（Research）や発注（Execution）基盤の構築をサポートします。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得（J-Quants API）と永続化（DuckDB）
- ETL パイプライン（日次差分更新・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ベースのニュース収集（前処理・銘柄抽出・DB 保存）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量探索（IC 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env 自動ロード、環境変数）

設計方針としては、DuckDB を中心に SQL + Python で処理を行い、本番口座・発注 API への直接アクセスを行わないモジュール（Data / Research）と、発注/監視など実行に関わるモジュールを分離しています。

---

## 機能一覧

主な機能の抜粋：

- 環境設定
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - settings オブジェクト経由で主要設定値を取得
- データ取得（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ等の堅牢な実装
  - DuckDB への冪等保存（ON CONFLICT）
- ETL（kabusys.data.pipeline）
  - 日次 ETL（calendar, prices, financials）の差分取得・保存、品質チェック統合
  - 差分更新、backfill、営業日調整
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返却
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・XML パース（defusedxml）・前処理
  - URL 正規化・トラッキングパラメータ除去・記事ID（SHA-256）生成
  - SSRF 対策（リダイレクト検査・プライベートアドレス禁止）・サイズ上限
  - raw_news / news_symbols への冪等保存
- 研究（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 正規化ユーティリティの再利用（zscore_normalize）
- スキーマ管理（kabusys.data.schema / audit）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査ログテーブル（signal_events, order_requests, executions）初期化ユーティリティ
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

※ 以下は最小限の手順例です。実運用では仮想環境（venv / conda 等）を推奨します。

1. Python (3.10+) を用意する
2. リポジトリをクローン / 配置する
3. 必要パッケージをインストールする（最低限）
   - duckdb
   - defusedxml
   - 他、標準ライブラリのみで実装された箇所が多いですが、実行環境で必要となるライブラリを適宜追加してください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ配布用に setup / pyproject を設定している場合:
# pip install -e .
```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が置かれたディレクトリ）に `.env` / `.env.local` を置くと自動でロードされます（アプリ起動時）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する

主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用）（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）

---

## 使い方（クイックスタート）

以下はライブラリ API を直接呼び出す簡単な例です。スクリプトからこれらを呼び出してバッチジョブ等を組めます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH から設定されます
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集を行う
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードセット (例: {"7203","6758",...})
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(), timeout=30)
print(res)
```

4) 研究用ファクターを計算する
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from datetime import date

records = calc_momentum(conn, target_date=date(2025, 1, 31))
fwd = calc_forward_returns(conn, target_date=date(2025, 1, 31))
# IC の計算例（factor_col と return_col を指定）
ic = calc_ic(records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

5) J-Quants API を直接操作（トークンの取得・データフェッチ）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,12,31))
```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得, 保存）
    - news_collector.py             — RSS ニュース収集・前処理・DB 保存
    - schema.py                     — DuckDB スキーマ定義 / 初期化
    - pipeline.py                   — ETL パイプライン（差分更新 / 日次 ETL）
    - quality.py                    — データ品質チェック
    - etl.py                        — ETL 公開インターフェース（ETLResult 等）
    - features.py                   — 特徴量ユーティリティの公開（zscore 再エクスポート）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                      — 監査ログ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリー等
  - strategy/                       — 戦略レイヤー（placeholder）
  - execution/                      — 発注実行レイヤー（placeholder）
  - monitoring/                     — 監視/メトリクス（placeholder）

各モジュールは docstring と関数説明で使用法が明記されています。`data.schema` によるテーブル定義は Raw / Processed / Feature / Execution 層に分かれており、監査ログは `data.audit` から別途初期化できます。

---

## 運用上の注意

- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml のある親）を基準に行われます。CWD に依存しない設計です。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストや CI 向け）。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client は内部でスロットリング・リトライを実装しています。大量取得の際はこの挙動に注意してください。
- DuckDB への書き込みは多くの箇所で ON CONFLICT（冪等保存）やトランザクション管理を行っていますが、外部から DB を直接操作する場合は一貫性を保つよう注意してください。
- news_collector は外部 RSS の取得に際して SSRF/サイズ攻撃対策を実装していますが、ソースの追加時は慎重に URL を検討してください。

---

## 貢献 / 拡張

- strategy / execution / monitoring パッケージはプレースホルダとして用意されています。ここに実取引ロジック・発注アダプタ・監視ロジックを実装できます。
- 新しい ETL チェックや特徴量の追加は data/quality.py や research/factor_research.py を拡張してください。
- DuckDB スキーマ変更時は data/schema.py を更新し、マイグレーション方針を策定してください。

---

README に記載のない点や、サンプルスクリプトの追加、実運用向けのデプロイ手順（サービス化、監視、バックアップ等）について要望があれば教えてください。必要に応じて README を追記します。