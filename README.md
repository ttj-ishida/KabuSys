# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDB ベースのデータスキーマといった機能を備え、研究（リサーチ）→ 本番運用のワークフローを想定しています。

---

## 主な特徴（概要）

- J-Quants API クライアント（レート制御・リトライ・トークン自動刷新）
- DuckDB ベースのスキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得、バックフィル対応、品質チェック連携）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（正規化・フィルタ・features テーブルへの冪等書き込み）
- シグナル生成（複数コンポーネントのスコア統合、Bear フィルタ、BUY/SELL）
- バックテストフレームワーク（シミュレータ、評価指標の計算、日次ループ）
- ニュース収集（RSS 取得、前処理、記事・銘柄紐付け、SSRF対策）
- 汎用統計ユーティリティ（Z スコア正規化、IC・ランク等）

---

## 依存・動作要件

- Python 3.10+
- pip でインストールする主なパッケージ:
  - duckdb
  - defusedxml

※ その他の標準ライブラリのみで多くを実装しているため、外部依存は最小限に抑えられています。

例（仮想環境作成後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージ化されている場合:
# pip install -e .
```

---

## 環境変数（必須 / 任意）

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須（Runtime にて呼ばれる設定）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabu ステーション API パスワード（execution 層で必要）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV - 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH - DuckDB ファイルパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH - SQLite（監視用）パス。デフォルト `data/monitoring.db`

---

## データベース初期化

DuckDB スキーマを初期化する関数が用意されています。初回は必ず実行してください。

例:
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリは自動作成されます）
conn = init_schema("data/kabusys.duckdb")
conn.close()

# インメモリ DB（テスト用）
conn = init_schema(":memory:")
```

init_schema() は全テーブル（raw, processed, feature, execution 層）を作成します（冪等）。

---

## 使い方（代表的なワークフロー / API）

以下は主要ユースケースの簡単な使用例です。各関数はモジュールからインポートして使用します。

1) ETL（株価データ差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")  # 初回のみ
# 既存 DB に接続する場合:
# conn = get_connection("data/kabusys.duckdb")

res = run_prices_etl(conn, target_date=date.today())
# ETLResult 型の戻り値（処理件数や品質問題・エラーメッセージを含む）
```

2) ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
```

3) 特徴量生成 / シグナル生成
```python
import duckdb
from datetime import date
from kabusys.strategy import build_features, generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
cnt = build_features(conn, target_date=date(2024, 1, 10))
signals_count = generate_signals(conn, target_date=date(2024, 1, 10))
```

4) バックテスト CLI
- コマンドラインから実行:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
- もしくはプログラムから:
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
# result.history, result.trades, result.metrics を参照
```

---

## 開発・デバッグのヒント

- 設定は Settings オブジェクト経由で取得できます:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```
- .env/.env.local の自動読み込みはプロジェクトルートを基準に行われます。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新が実装されています。テストでは id_token を明示的に注入して制御できます。
- ニュース収集は SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）を行っています。外部への HTTP 呼び出しをモックして単体テストを行うと良いです。
- バックテストは本番 DB を直接変更しないために、必要なテーブルをインメモリ DB にコピーして実行します（_build_backtest_conn）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント（取得・保存）
  - news_collector.py                 — RSS ニュース収集・保存・銘柄抽出
  - pipeline.py                       — ETL パイプライン（差分取得 / 品質チェック連携）
  - schema.py                         — DuckDB スキーマ定義・初期化
  - stats.py                          — 統計ユーティリティ（Z スコア等）
- strategy/
  - __init__.py
  - feature_engineering.py            — 特徴量構築（正規化・ユニバースフィルタ）
  - signal_generator.py               — シグナル生成（final_score 計算・BUY/SELL）
- research/
  - __init__.py
  - factor_research.py                — モメンタム/ボラティリティ/バリュー算出
  - feature_exploration.py            — 将来リターン / IC / 統計サマリ
- backtest/
  - __init__.py
  - engine.py                         — バックテストエンジン（run_backtest）
  - simulator.py                      — ポートフォリオシミュレータ（擬似約定）
  - metrics.py                        — バックテスト評価指標計算
  - run.py                            — CLI エントリポイント
  - clock.py                          — 模擬時計（将来拡張用）
- execution/                           — （発注 / execution 関連: 空パッケージ）
- monitoring/                          — （監視用モジュール等: 空パッケージ）

ドキュメント候補ファイル（コード内コメント参照）:
- StrategyModel.md, DataPlatform.md, BacktestFramework.md, DataSchema.md 等（実運用時の仕様書）

---

## 注意事項 / 設計ポリシー

- ルックアヘッドバイアス回避: すべての分析 / シグナル生成は target_date 時点までに「システムが知り得る」データのみを使用する設計です（fetched_at の記録や target_date の前方参照制御により保証）。
- 冪等性: DB 書き込みは ON CONFLICT / トランザクションを用いて冪等に行うよう実装されています。重複挿入や再実行に耐えられることを意図しています。
- 安全対策: ニュース収集の SSRF 対策、XML パースの安全化、API レート制御とリトライなど運用で必要な堅牢性を考慮しています。

---

もし README に含めたい追加の使用例（例: CI設定、運用 cron ジョブ、Slack通知設定、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env.example を作成することもできます。