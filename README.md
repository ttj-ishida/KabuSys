# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査・スキーマ管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーを持つ、研究〜本番まで使える日本株アルゴリズム取引プラットフォームの基盤モジュール群です。

- Data 層: J-Quants から市場データ／財務データ／カレンダーを取得し、DuckDB に保存する ETL。
- Feature 層: research モジュールで算出した生ファクターの正規化・合成（features テーブル作成）。
- Strategy 層: features と AI スコアを統合して売買シグナルを生成（signals テーブル作成）。
- Execution / Audit 層: シグナル→発注→約定→ポジション管理のための DB スキーマと監査ログ。

設計上のポイント:
- ルックアヘッドバイアス回避（各処理は target_date 時点の情報だけを使用）
- 冪等性（DB への保存は ON CONFLICT などで上書きやスキップ）
- 外部 API 呼び出し時のリトライ／レート制御／トークン自動リフレッシュ
- DuckDB を中心としたローカル DB 管理

---

## 主な機能一覧

- jquants_client:
  - J-Quants API から株価・財務・カレンダーをページネーション対応で取得
  - レートリミット／リトライ／401時のトークン自動再取得
  - DuckDB への冪等保存(save_daily_quotes / save_financial_statements / save_market_calendar)
- data.pipeline:
  - 日次 ETL の実行（run_daily_etl）
  - 差分取得ロジック、バックフィル、品質チェック呼び出し
- data.schema:
  - DuckDB スキーマの定義と初期化（init_schema）
- data.news_collector:
  - RSS 取得・前処理・記事 ID 生成・raw_news への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- data.calendar_management:
  - market_calendar 管理と営業日判定ユーティリティ（is_trading_day, next_trading_day 等）
- research:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC（calc_forward_returns, calc_ic）
  - 統計ユーティリティ（factor_summary, rank）
- strategy:
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
- settings / config:
  - .env ファイル（.env / .env.local）および環境変数の自動読み込み
  - 必須環境変数の抽出と検証

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーション Path | None 等を使用）
- DuckDB を利用するため、必要な環境であること

1. リポジトリをクローンまたは配置
2. 仮想環境を作る（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. パッケージをインストール（最低限の依存）
   - 必要なパッケージ（例）:
     - duckdb
     - defusedxml
   pip でインストールする例:
   ```
   python -m pip install -U pip
   python -m pip install duckdb defusedxml
   ```
   （プロジェクト配布に合わせて requirements.txt / pyproject.toml を用意してください）
4. editable install（開発向け）
   ```
   python -m pip install -e .
   ```

---

## 環境変数（.env）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数と説明:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（get_id_token に使用）
- kabuステーション API
  - KABU_API_PASSWORD (必須): kabu API パスワード
  - KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
  - SQLITE_PATH (任意): デフォルト data/monitoring.db
- 実行モード / ログ
  - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
  - LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- .env のパースはクォートやコメントに対して比較的寛容に実装されています。
- OS 環境変数が優先されます。.env.local は .env を上書きします。

---

## 使い方（コード例）

以下は主要なユースケースの簡単な使用例です。DuckDB の接続には `:memory:` を使えばメモリ DB でテスト可能です。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 研究用ファクター計算・特徴量構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと紐付けが実行されます
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

6) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数/設定管理（自動 .env ロード、settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン、run_daily_etl 等
  - schema.py — DuckDB スキーマ定義と init_schema
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - news_collector.py — RSS 取得・前処理・DB 保存
  - calendar_management.py — market_calendar 管理、営業日判定
  - features.py — features 用ユーティリティ公開
  - audit.py — 監査ログスキーマ
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築（build_features）
  - signal_generator.py — generate_signals（買い・売りシグナル生成）
- execution/ — (発注用モジュールのプレースホルダ)
- monitoring/ — (監視・メトリクス用のプレースホルダ)

---

## 注意事項 / 運用メモ

- DuckDB のファイルパスは settings.duckdb_path で管理。CI や一時実行では ":memory:" を使うと便利。
- J-Quants API のレート制限（120 req/min）に注意。クライアントは内部で固定間隔スロットリングを行いますが、バッチ設計時に考慮してください。
- ETL は差分取得の仕組みを持ちますが、初回ロードやフルバックフィルは実行対象によって時間がかかる可能性があります。
- 本ライブラリは発注（execution）実装と本番連携のためのスキーマとユーティリティを備えますが、実際の証券会社との連携ロジック（kabu 接続など）は別途実装が必要です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。テストで自動読み込みを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベース（src/kabusys 以下）の現在実装状況に基づき作成しています。実運用や拡張の際は DataPlatform.md / StrategyModel.md 等の仕様ドキュメントと合わせて参照してください。必要であれば利用例やデプロイ手順、CI テスト手順を追加で作成します。