# KabuSys

KabuSys は日本株のデータ取得・ETL・特徴量作成・シグナル生成・ニュース収集・監査までをカバーする自動売買支援ライブラリです。本リポジトリは研究用のファクター計算や運用向けのETL／データベーススキーマ、戦略ロジックの骨格を提供します。

主な設計方針:
- ルックアヘッドバイアス対策（計算は target_date 時点の利用可能データのみを使用）
- DuckDB を中心に冪等性（ON CONFLICT / トランザクション）を重視
- 外部 API（J-Quants）へのアクセスは rate-limit / リトライ / トークン自動リフレッシュを考慮
- ネットワーク周り（RSS収集）は SSRF や XML Bomb 対策を実施

## 機能一覧
- データ取得・保存
  - J-Quants からの株価日足・財務データ・市場カレンダー取得（jquants_client）
  - raw / processed / feature / execution 層を含む DuckDB スキーマ定義と初期化（data.schema）
  - 差分 ETL パイプライン（data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質・カレンダー管理
  - market_calendar を用いた営業日判定・前後営業日取得（data.calendar_management）
- ニュース収集
  - RSS 取得・前処理・記事保存（data.news_collector）
  - 銘柄コード抽出・記事⇄銘柄の紐付け
- 研究 / ファクター処理
  - momentum/volatility/value などのファクター計算（research.factor_research）
  - 将来リターン計算 / IC 計算 / 統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats）
- 戦略
  - 特徴量作成（strategy.feature_engineering: build_features）
  - シグナル生成（strategy.signal_generator: generate_signals）
- 監査 / 発注フロー用テーブル
  - signal_events / order_requests / executions など監査用スキーマ（data.audit）

## セットアップ手順

前提
- Python 3.9+（ソースは型アノテーションに union 型などを使用）
- DuckDB が必要（pip 経由でインストール可能）
- defusedxml（RSS/XM Lパースの安全対策）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数
- 本ライブラリは環境変数から設定を読み込みます（kabusys.config.Settings）。
  主なキー:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabu API パスワード（必須）
  - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で環境変数を自動読み込みします。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env の最小例（実際の値を設定してください）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（基本的なコード例）

以下は主要な操作の Python での使用例です。実行前に必要な環境変数を設定し、DuckDB のファイルパスが適切であることを確認してください。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL を実行（J-Quants から差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)  # target_date は省略で今日を使用
print(res.to_dict())
```

3) マーケットカレンダーの夜間更新ジョブ（単体）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

4) ニュース（RSS）収集
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効な銘柄コードのセット（例: {'7203','6758',...}）
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: saved_count, ...}
```

5) 特徴量作成（build_features）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, date(2024, 1, 10))
print("features upserted:", n)
```

6) シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, date.today())  # threshold や weights を渡して上書き可
print("signals generated:", count)
```

7) 研究用ユーティリティ（将来リターン・IC）
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, date.today(), horizons=[1,5,21])
# factor_records は研究モジュールが返すリスト（例: calc_momentum の戻り値）
rho = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_5d")
```

注意:
- 多くの関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取ります。接続は init_schema() が返すもの、または get_connection() で取得してください。
- ETL / 保存関数は冪等性を考慮しているため、複数回実行しても重複を上書きします。

## ディレクトリ構成（主要ファイル）
（プロジェクトルートが src/ 配下の Python パッケージ構成を想定）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                      — DuckDB スキーマ定義と init_schema
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - pipeline.py                    — 日次 ETL / 差分更新ロジック
    - news_collector.py              — RSS 収集・保存・銘柄抽出
    - calendar_management.py         — カレンダー管理（営業日判定等）
    - audit.py                       — 監査ログテーブル DDL
    - features.py                    — data.stats の再エクスポート
    - stats.py                       — Zスコアなど統計ユーティリティ
    - execution/                      — 発注 / 実行関連（未詳細実装）
  - research/
    - __init__.py
    - factor_research.py             — momentum/volatility/value の計算
    - feature_exploration.py         — 将来リターン/IC/summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features 作成（build_features）
    - signal_generator.py            — シグナル生成（generate_signals）
  - monitoring/                      — 監視系（SQLite 等、未詳細実装）
  - execution/                       — 実際の発注実装（kabu 層、未詳細実装）

（上記は本リポジトリに含まれる主要モジュールです。詳細はソースを参照してください）

## 注意事項・運用上のポイント
- 環境: KABUSYS_ENV を "live" にした場合は実際の発注等を行う想定になります。paper_trading / development の設定を適切に使い分けてください。
- 認証トークン: J-Quants のリフレッシュトークンは厳重に管理してください。config.get_id_token は自動でトークンを更新します。
- ネットワーク/セキュリティ: RSS 収集・URL 処理には SSRF や XML Bomb 対策を導入していますが、運用環境でもネットワーク制限を行ってください。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env 自動読み込みを無効化できます（テスト時に環境を固定したい場合に有用）。

---

詳細な仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）は別ドキュメントで管理する想定です。まずは上記の手順で DB 初期化 → ETL → feature 作成 → signal 生成 の流れを試し、必要に応じて独自の戦略重みや閾値を与えてカスタマイズしてください。質問や追加で README に載せたい例があれば教えてください。