# KabuSys

日本株向けの自動売買プラットフォームライブラリ。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、DuckDB スキーマなど、戦略バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群から構成されます。

- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存する ETL（差分更新／冪等保存）。
- DuckDB 上でのデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化。
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量正規化ユーティリティ。
- 特徴量から戦略用の最終スコアを作成し、BUY/SELL シグナルを生成するロジック（閾値、重み、Bear フィルタ、エグジット判定等を実装）。
- RSS などからニュースを収集し、記事と銘柄の紐付けを行うニュースコレクタ（SSRF・XML攻撃・サイズ制限などの防御あり）。
- JPX カレンダー管理（営業日判定、next/prev trading day、定期更新ジョブ）。
- audit 用の監査ログテーブル（発注〜約定フローの完全トレースを想定）。

設計方針としては「ルックアヘッドバイアスの防止」「冪等性」「外部依存を最小化（標準ライブラリ中心）」「DuckDB を中核にしたデータ設計」が採用されています。

---

## 主な機能一覧

- データ取得／ETL
  - J-Quants から株価（日足）・財務データ・マーケットカレンダーを取得（ページネーション・リトライ・レート制御）
  - 差分更新、バックフィル対応、品質チェックとの連携
- データスキーマ
  - DuckDB に Raw / Processed / Feature / Execution 層のテーブルを作成（init_schema）
- 研究・ファクター算出
  - モメンタム、ボラティリティ、バリュー系ファクター（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン・IC（Spearman）や統計サマリー
- 特徴量 → シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL の生成・保存（signals テーブル）
  - エグジット判定（ストップロス等）
- ニュース収集
  - RSS 取得、前処理、記事ID生成、raw_news 保存、銘柄抽出と news_symbols 紐付け
  - SSRF / XML 攻撃 / レスポンスサイズ制御などの安全対策
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間の calendar_update_job による差分更新
- 監査ログ（audit）
  - signal_events / order_requests / executions など、発注〜約定のトレース用スキーマ

---

## 必要条件（実行環境）

- Python 3.10+
  - Path | None や型ヒントの記法（Python 3.10 の構文）を使用しています。
- 必要なパッケージ（主な例）
  - duckdb
  - defusedxml
  - （ネットワーク経由で利用するため urllib は標準ライブラリで提供）

pip での例:
```
pip install duckdb defusedxml
```

パッケージング済みであれば:
```
pip install -e .
```
のようにインストールして利用できます（セットアップスクリプトがある場合）。

---

## 環境変数（設定）

kabusys は .env ファイルまたは環境変数から設定を自動読み込みします（プロジェクトルート判定は .git または pyproject.toml を起点）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)

設定はコード上で `from kabusys.config import settings` からアクセス可能です。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカルでの初期化例）

1. リポジトリを取得
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   ```

   （プロジェクトが packaging されている場合は `pip install -e .`）

4. 環境変数を設定（.env をプロジェクトルートに作成）
   - 上の「環境変数」セクションを参考に必要なものを設定してください。

5. DuckDB スキーマの初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```

---

## 使い方（基本例）

以下は主要な処理を呼び出す簡単なサンプルです。

- 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（今日分）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

conn.close()
```

- 特徴量の構築（指定日）
```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 5), threshold=0.6)
print(f"signals written: {count}")
conn.close()
```

- ニュース収集の実行
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

---

## 主要 API（モジュールと関数）

- kabusys.config.settings — 環境変数から設定を取得
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL の統合実行
- kabusys.data.jquants_client.* — J-Quants API クライアント（fetch_*/save_*）
- kabusys.data.news_collector.run_news_collection(...) — ニュース収集
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)

各関数はドキュメンテーション文字列（docstring）で引数・戻り値・動作保障（冪等性や例外挙動）について説明しています。実装中の仕様は docstring を参照してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py              — RSS ニュース収集・前処理・DB保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                    — ETL パイプライン（差分取得・backfill・品質検査）
    - calendar_management.py         — 市場カレンダー管理・ジョブ
    - audit.py                       — 発注〜約定の監査ログスキーマ
    - features.py                    — features 再エクスポート（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/volatility/value）
    - feature_exploration.py         — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py            — final_score 計算・BUY/SELL シグナル生成
  - execution/                        — （発注実行レイヤー。現時点では空の __init__）
  - monitoring/                       — 監視関連（DB: sqlite 等）用モジュール（別ディレクトリ）
  - その他：ユーティリティや将来的なモジュール群

---

## 運用上の注意点

- 環境変数の管理（特に JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / Slack トークン）は厳重に行ってください。
- DuckDB ファイルは永続化先（デフォルト data/kabusys.duckdb）を適切にバックアップしてください。
- J-Quants の API レート制限（120 req/min）やレスポンスの変動を考慮して ETL のスケジュールを設計してください（ライブラリ側でレート制御とリトライは実装済み）。
- ニュース収集や外部 URL 取得には SSRF 対策が組み込まれていますが、運用環境ではネットワークポリシーで更に制限することを推奨します。
- KABUSYS_ENV は運用フロー（paper_trading / live など）に影響する可能性があるため、適切に設定してください。

---

## 貢献・拡張

- 新しいファクター、AI スコアの導入、execution 層（ブローカー連携）の実装、品質チェックの追加などが想定拡張項目です。
- コードの多くは docstring に設計意図と前提（例: ルックアヘッド回避、冪等性）を記載しています。拡張時はこれらの前提を保つように実装してください。

---

README に書ききれない詳細な仕様（StrategyModel.md / DataPlatform.md 等）はコード内 docstring と別ドキュメントに記載されている想定です。必要であればそれらの設計ドキュメントの要約や追加の使用例を作成します。どの部分を優先して詳述しますか？