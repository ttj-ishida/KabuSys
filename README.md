# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ管理、監査ログ等のユーティリティを含むモジュール群です。

---

## 概要

KabuSys は以下を目的とした内部ライブラリ／ツール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- データ品質チェックを組み込んだ日次 ETL パイプライン
- リサーチで得た生ファクターをもとに戦略用特徴量を構築（Z スコア正規化等）
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成（BUY/SELL）
- RSS からのニュース収集と銘柄紐付け（SSRF対策やサイズ制限あり）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- 発注・約定・監査のためのテーブル設計（監査ログ用DDL）

設計上、発注 API や実際のブローカー接続（execution 層）への直接依存は排除し、データ層と戦略層の核となる処理に集中しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制限、再試行、トークン自動更新、ページネーション対応）
  - 生データを DuckDB に冪等保存する save_* 関数群
- data/schema.py
  - DuckDB のテーブル定義と初期化（init_schema）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）、個別 ETL ジョブ（prices / financials / calendar）
- data/news_collector.py
  - RSS フィード収集（SSRF 防御、gzip 対応、トラッキングパラメータ除去、記事ID生成）
  - raw_news / news_symbols への保存ユーティリティ
- data/calendar_management.py
  - market_calendar を元にした営業日判定・前後営業日取得等のユーティリティ
- research/factor_research.py
  - momentum / volatility / value 等のファクター計算
- research/feature_exploration.py
  - 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/feature_engineering.py
  - リサーチファクターを正規化・合成して features テーブルへアップサート
- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を算出し signals テーブルへ保存
- data/stats.py
  - z-score 正規化ユーティリティ
- config.py
  - .env / 環境変数読み込み、Settings オブジェクト経由で設定管理

---

## 要件（推奨）

- Python 3.10 以上（| 型ヒントなどを使用）
- 必要なパッケージ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリを主に使用（urllib 等）

※ 実際のプロジェクトでは requirements.txt や pyproject.toml を追加して依存管理してください。

基本的なインストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# あるいはプロジェクトに setup / pyproject があれば:
# pip install -e .
```

---

## 環境変数（Settings）

config.Settings から参照される主要な環境変数は以下です。`.env` に記載してプロジェクトルートに置くと自動読み込みされます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注 API を使う場合）
- SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID

オプション（デフォルトあり）:
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

例: `.env`
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境を作成して有効化する
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数を設定（プロジェクトルートに .env を置くのが簡単）
   - 上の「環境変数」セクションを参照して `.env` を作成

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトから実行:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（主要 API・ワークフロー例）

以下は基本的な日次処理の流れの例です。

1) 日次 ETL の実行（市場カレンダー取得 → 株価/財務の差分取得 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の作成（research モジュールでの生ファクターを正規化して features テーブルへ）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナル生成（features と ai_scores を統合して signals を作成）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today())
print(f"signals generated: {count}")
```

4) RSS ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes: 既知の銘柄コード集合（例: prices_daily から抽出）
known_codes = {"7203", "6758", "9984"}  # 例
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(result)
```

5) J-Quants のトークン取得（必要に応じて直接呼び出し）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

---

## 留意点 / 実装上の設計メモ

- レート制限: J-Quants は 120 req/min、client は固定間隔スロットリングで制御
- 再試行: 408/429/5xx に対して指数バックオフで再試行、401 はトークンを自動更新して再試行
- 冪等性: raw データ保存は ON CONFLICT DO UPDATE / DO NOTHING により冪等性を確保
- Look-ahead bias 防止: 取得時の fetched_at を UTC で記録
- NewsCollector は SSRF 対策、gzip サイズ制限、トラッキングパラメータ除去など堅牢化実装
- シグナル生成は Bear レジーム抑制・ストップロス等のルールを実装（StrategyModel.md 相当の仕様が参照される想定）
- 設定は .env から自動読み込み（プロジェクトルート検出は .git または pyproject.toml を起点）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルとモジュール配置（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - (execution/ など)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (監視関連のユーティリティ想定)

上記はファイル単位で機能が分割されています。詳細はソースツリーを参照してください。

---

## 開発・運用上のヒント

- テスト時や CI では環境変数の自動ロードを抑止したいことがあるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用できます。
- DuckDB のパスを `:memory:` にすればインメモリ DB でテスト可能。
- ETL のバックフィルやカレンダー先読みは pipeline.run_daily_etl の引数で調整可能。
- production（live）モードへ切り替えると is_live フラグが True になりますが、発注等の実行は十分な安全確認の上で行ってください。

---

## ライセンス・貢献

本 README はコードベースから抽出した使用方法の簡易ガイドです。実運用・公開配布する場合は適切なライセンス表記、セキュリティ監査、追加の依存管理（pyproject.toml / requirements.txt）、ユニットテストを整備してください。

ご質問や追加したい使用例があれば教えてください。README を要望に合わせて拡張します。