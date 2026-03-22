# KabuSys

日本株向けの自動売買 / 研究プラットフォームのコアライブラリです。データ取得・ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集などの主要機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーを備えたモジュール群で構成されています。

- データ収集・保存（J-Quants からの株価 / 財務 / カレンダー取得、RSS ニュース収集）
- データスキーマ（DuckDB）と ETL パイプライン
- 研究用ファクター計算・特徴量正規化（research）
- 戦略（feature_engineering, signal_generator）
- バックテストエンジン（擬似約定・ポートフォリオ管理・メトリクス）
- 実運用レイヤ（execution）および監視（monitoring）用の基盤

設計方針の一例:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を中心に冪等な保存（ON CONFLICT / INSERT .. DO UPDATE）
- ネットワーク処理にリトライ／レートリミット、SSRF 対策等を導入

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（トークンリフレッシュ、ページネーション、保存関数）
  - news_collector: RSS からニュース取得、正規化、DB 保存、銘柄抽出
  - schema: DuckDB のスキーマ定義 / 初期化（init_schema）
  - pipeline: 差分ETL、品質チェック（ETLResult 型）
  - stats: z-score 正規化などのユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナル作成
- backtest/
  - engine.run_backtest: DuckDB データをコピーして日次ベースのバックテストを実行
  - simulator.PortfolioSimulator: 擬似約定・履歴管理
  - metrics.calc_metrics: バックテスト評価指標計算
  - run: CLI でのバックテスト実行エントリポイント

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（少なくとも以下が必要）
  - duckdb
  - defusedxml
- （ネットワーク関連の機能を使う場合）インターネット接続、J-Quants リフレッシュトークン

requirements.txt はプロジェクトに含まれていないため、環境に応じて必要ライブラリをインストールしてください。

例:
pip install duckdb defusedxml

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは環境変数から設定を読み込みます（自動ロード機能あり）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

例 .env（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は Python から `from kabusys.config import settings` を使って参照できます（settings.jquants_refresh_token、settings.duckdb_path 等）。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / コピー

2. Python 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

4. 環境変数（.env）を作成
   - プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合は手動で設定）。

5. DuckDB スキーマ初期化
   - Python REPL で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - これにより必要なテーブルがすべて作成されます。

---

## 使い方（主要操作例）

以下は代表的な操作の例です。

1) DB スキーマ初期化（一度）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) J-Quants からデータ取得 / 保存（jquants_client を利用）
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

3) RSS ニュース収集と DB 保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けも行う
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(result)
conn.close()
```

4) 特徴量作成（features テーブル生成）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print("features upserted:", n)
conn.close()
```

5) シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31))
print("signals written:", count)
conn.close()
```

6) バックテスト（CLI）
プロジェクトにはバックテスト実行のエントリポイントがあります。DB は事前に prices_daily, features, ai_scores, market_regime, market_calendar 等が入っている必要があります。

コマンド例:
```sh
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

出力はバックテスト結果（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を表示します。

---

## API（よく使う関数抜粋）

- kabusys.config.settings: 環境設定プロパティ（jquants_refresh_token, duckdb_path, env, log_level 等）
- kabusys.data.schema.init_schema(db_path): DuckDB のスキーマ作成・接続取得
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline.run_prices_etl / run_news_collection 等（ETL ジョブ管理）
- kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)

（詳細は各モジュールの docstring を参照してください。）

---

## ディレクトリ構成

主要なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/    (発注用モジュール群、未実装ファイルも含む)
  - monitoring/   (監視 / メトリクス格納用等)

（実際のリポジトリではさらにテストやドキュメント、CI 設定等が含まれる可能性があります）

---

## 運用上の注意・補足

- 環境変数の自動ロードは .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から読込む実装です。テスト時などに自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）や 401 の自動リフレッシュ、リトライ制御が組み込まれていますが、API 利用上のルール遵守は運用者の責任です。
- DuckDB スキーマは多くの制約・インデックスが定義されており、データ品質保守のため ETL 側で前後処理（backfill、品質チェック）を想定しています。
- 実運用（live）モードでは KABUSYS_ENV=live を設定してください。paper_trading など切り替えが可能です。

---

必要であれば、README に「インストール手順（pip パッケージ化）」「開発ルール」「テスト実行方法」「詳細な API リファレンス」などの追加セクションを作成します。どの情報を追加しますか？