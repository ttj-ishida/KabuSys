# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
DuckDB をデータレイヤに採用し、J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して ETL → 品質チェック → 特徴量生成 → 戦略評価までをサポートします。ニュース収集や監査（発注 → 約定のトレーサビリティ）機能も備えています。

---

## 概要

主な目的は次の通りです。

- J-Quants API からの差分取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB によるデータ永続化（Raw / Processed / Feature / Execution 層のスキーマ定義）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と評価（IC、統計サマリー）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- カレンダー（営業日判定・前後営業日取得）ユーティリティ

設計方針として、本パッケージの多くのモジュールは「DuckDB 接続を受け取り SQL を実行する」形で実装されており、本番発注 API には直接アクセスしません（データ層と実行層の責務分離）。

---

## 主な機能一覧

- 環境変数/設定読み込み（.env 自動ロード、.env.local 上書き）
- J-Quants クライアント（認証・ページネーション・レート制御・リトライ・保存ユーティリティ）
- DuckDB 用スキーマ定義 / 初期化（data.schema.init_schema）
- 日次 ETL（data.pipeline.run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
- ニュース収集（RSS 取得、正規化、raw_news 保存、銘柄抽出）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究モジュール（factor_research / feature_exploration、IC・統計要約）
- 統計ユーティリティ（zscore 正規化）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
- 監査スキーマ（signal_events, order_requests, executions 等）

---

## 動作要件（概略）

- Python 3.9+
- 必要な主要ライブラリ（例）:
  - duckdb
  - defusedxml

（パッケージとして配布する場合は setup/pyproject の依存に従ってインストールしてください）

---

## 環境変数 / 設定

自動的にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探し、以下の優先順位で .env を読み込みます:

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須・よく使う環境変数（モジュール `kabusys.config.Settings` が参照）:

- JQUANTS_REFRESH_TOKEN （必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD （必須）: kabuステーション API パスワード
- KABU_API_BASE_URL （任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID （必須）: Slack チャンネルID
- DUCKDB_PATH （任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （任意）: 監視用途などの SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV （任意）: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL （任意）: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env に書く例（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発向け）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（例）:
   - pip install duckdb defusedxml
   - もしパッケージ配布があれば pip install -e . 等

4. プロジェクトルートに .env（または .env.local）を用意して必須値を設定

---

## 使い方（コード例）

以下は主要ユースケースのサンプルです。Python スクリプトや REPL で実行できます。

- DuckDB スキーマ初期化（初回のみ）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース収集ジョブ（既知銘柄セットを与えて銘柄紐付けまで）
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄リスト
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants の生データ取得（低レベル API）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 研究用ファクター計算の実行例
```
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2024,3,1))
vols = calc_volatility(conn, target_date=date(2024,3,1))
vals = calc_value(conn, target_date=date(2024,3,1))

# Z スコア正規化（data.stats.zscore_normalize を利用）
all_recs = zscore_normalize(recs, columns=["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- マーケットカレンダーのユーティリティ
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day
conn = get_connection("data/kabusys.duckdb")
is_trade = is_trading_day(conn, date(2024,3,1))
next_day = next_trading_day(conn, date(2024,3,1))
```

---

## 主要 API のポイント

- data.schema.init_schema(db_path) はテーブル・インデックスを作成して DuckDB 接続を返します。":memory:" を指定するとインメモリ DB を使えます。
- data.pipeline.run_daily_etl(...) は ETLResult を返し、取得件数・保存件数・品質問題などを確認できます。
- jquants_client は内部でレート制御（120 req/min）とリトライ・トークンリフレッシュを備えています。get_id_token() で ID トークンを取得できます。
- news_collector.fetch_rss は SSRF 対策・gzip サイズ制限・XML デフューズ処理を行い、安全に RSS を処理します。
- data.quality.run_all_checks(conn, ...) でデータ品質チェックが実行できます（欠損・重複・スパイク・日付不整合）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（取得・保存）
  - news_collector.py         — RSS ニュース収集・保存・銘柄抽出
  - schema.py                 — DuckDB スキーマ定義 & init_schema
  - pipeline.py               — ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - features.py               — 特徴量ユーティリティ再エクスポート
  - stats.py                  — 統計ユーティリティ（z-score 等）
  - calendar_management.py    — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py                  — 監査ログスキーマ（signal / order_request / executions）
  - etl.py                    — ETL レイヤ公開インターフェース
  - quality.py                — データ品質チェック
  - (その他: pipeline/quality関連)
- research/
  - __init__.py
  - feature_exploration.py    — 将来リターン計算 / IC / 統計サマリー
  - factor_research.py        — Momentum / Volatility / Value 等の計算
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は主要ファイルを抜粋した構成です）

---

## 運用上の注意

- .env の自動読み込みはプロジェクトルートの検出に依存します。CI やテストで環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、明示的に環境変数を注入してください。
- J-Quants の API レート制限（120 req/min）に合わせてクライアント側でスロットリングを実装していますが、大量の銘柄をバッチで取得する場合はジョブ設計に注意してください。
- DuckDB の上書き/スキーマ変更は慎重に行ってください。init_schema は既存テーブルを上書きしない（IF NOT EXISTS）ため安全ですが、スキーマ変更時のマイグレーションは別途必要です。
- news_collector は外部 URL を扱うため SSRF/大容量レスポンス等の対策を組み込んでいますが、追加のセキュリティポリシーがある場合は更に制限してください。

---

## 参考・拡張ポイント

- strategy / execution モジュールはフレームワークとしての枠組みのみ用意されています。実際の注文ロジックやブローカー API 連携はプロジェクト特有の実装が必要です。
- 監査 (audit) テーブルは監査・調査用に詳細に設計されています。運用では order_request_id を冪等キーとして使うことを推奨します。
- DuckDB を利用することで SQL での高速な集計・特徴量計算が可能です。大規模データや分析ノードでの利用時はファイル配置・バックアップ戦略を検討してください。

---

ご不明点や README に加えたいサンプル（例えば CLI スクリプトや systemd / Airflow の運用例）があればお知らせください。必要に応じて README を拡張して具体的な運用手順や例を追加します。