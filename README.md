# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants からの市場データ取得、DuckDB でのデータ管理、特徴量計算・研究ユーティリティ、ニュース収集、ETL パイプライン、監査ログなど、戦略開発〜運用に必要な共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を包含する Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたスキーマ定義、冪等保存（ON CONFLICT）によるデータ永続化
- ETL パイプライン（差分取得 / バックフィル / 品質チェック）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- ファクター（モメンタム／バリュー／ボラティリティ等）計算、IC や統計サマリー
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針として、本番発注 API への不要なアクセスを行わないモジュール（research / data 等）と、実際の発注・監視を扱う execution/monitoring を分離しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
- data/schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline: 日次 ETL 実行（差分取得、バックフィル、品質チェック）
- data/news_collector: RSS 取得→正規化→DB 保存（SSRF 防御、トラッキング除去、記事ID の冪等化）
- data/quality: 欠損・スパイク・重複・日付不整合の検出
- data/calendar_management: JPX カレンダー更新と営業日ロジック
- data/audit: 発注〜約定の監査テーブル（トレーサビリティ）
- data/stats: zscore 正規化などの共通統計ユーティリティ
- research/factor_research: momentum / value / volatility 等のファクター計算
- research/feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリー
- config: 環境変数読み込み・管理（.env 自動読み込み機能あり）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `|` 演算子等を使用しています）
- Git（プロジェクトルート検出で .git / pyproject.toml を使用）

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   - 他に運用で使うライブラリ（例: slack SDK など）があれば適宜追加してください。

3. パッケージのインストール（プロジェクトに pyproject.toml/setup があれば）
   ```
   pip install -e .
   ```
   ない場合は、開発環境で `PYTHONPATH=src` を使うか、適切に path を通してください。

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（※自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   必須となる環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID — Slack チャンネルID（必須）
   任意の設定:
   - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視 DB などに使う sqlite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV — environment (development / paper_trading / live)。デフォルト development
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト INFO

   .env の読み込み優先順位:
   - OS 環境変数 > .env.local > .env
   - .env 自動ロードはプロジェクトルート（.git or pyproject.toml）を基準に行われます

---

## 使い方（簡単な例）

以下は主要なユースケースの例です。実行は Python スクリプトまたは REPL で行えます。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
# デフォルトのファイルパス settings.duckdb_path を使う場合:
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)
# メモリ DB を使う場合:
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants から取得 → DuckDB 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
# conn: DuckDB 接続（上で取得した conn）
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集（RSS を取得して raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コードのセット（紐付けに使用）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4) ファクター計算（研究用、データベース参照のみ）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# さらに zscore 正規化など
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```
- research モジュールは市場データ（prices_daily / raw_financials）のみを参照し、本番口座や発注 API にはアクセスしません。

5) J-Quants の生データフェッチ / 保存（必要に応じて個別に）
```python
from kabusys.data import jquants_client as jq
# 取得
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
# 保存
saved = jq.save_daily_quotes(conn, records)
```

---

## ディレクトリ構成

プロジェクトの主要なファイル / モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得/保存/認証/レート制御）
    - news_collector.py         # RSS 取得・前処理・DB 保存（SSRF 防御等）
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（差分取得・backfill・品質チェック）
    - stats.py                  # 統計ユーティリティ（zscore 等）
    - features.py               # features 公開インターフェース（zscore の再エクスポート）
    - calendar_management.py    # マーケットカレンダー管理・営業日判定
    - audit.py                  # 監査ログテーブル（order / execution トレーサビリティ）
    - etl.py                    # ETL 型/再エクスポート
    - quality.py                # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py    # 将来リターン計算、IC、統計サマリー
    - factor_research.py        # momentum/value/volatility ファクター計算
  - strategy/
    - __init__.py               # 戦略関連のエントリポイント（未実装枠）
  - execution/
    - __init__.py               # 発注 / 実行層（未実装枠）
  - monitoring/
    - __init__.py               # 監視 / メトリクス（未実装枠）

各モジュールは設計上、データ取得/加工と実際のブローカ発注ロジックを分離しています。研究・テスト用途の関数は外部発注を行わないため、安心して分析に利用できます。

---

## 注意事項 / 運用メモ

- 環境変数の取り扱い
  - 自動で .env / .env.local をプロジェクトルートから読み込む仕組みがあります。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
  - settings（kabusys.config.settings）経由で各種設定値を参照します。必須値がない場合は ValueError が上がります。

- J-Quants API
  - レート制限（120 req/min）を考慮した固定間隔スロットリングとリトライロジックが組み込まれています。
  - 401 発生時はリフレッシュトークンで自動更新し 1 回リトライします。

- ニュース収集
  - RSS の取得は SSRF 対策、gzip 上限チェック、XML パースの安全実装（defusedxml）などを設けています。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を担保します。

- DuckDB スキーマ
  - init_schema() は冪等にテーブルとインデックスを作成します。audit の初期化や別 DB での監査ログ管理もサポートします。

- 品質チェック
  - run_all_checks() は複数チェックを実行して問題の一覧 (QualityIssue) を返します。致命度に応じた処理は呼び出し側で判断してください（Fail-Fast ではありません）。

---

この README はコードベースの主要機能の概要と利用法をまとめたものです。具体的な設定例 (.env.example)、CI 設定、Slack 通知や broker 接続などの実運用に関わる設定はプロジェクトの他ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照し、適宜補完してください。質問やサンプルスクリプトが必要であればお知らせください。