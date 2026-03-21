# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）→ ETL → 特徴量生成 → シグナル生成 → 発注／監視 の流れを想定したモジュール群を含みます。研究（research）用途のユーティリティも同梱しており、戦略の探索・評価〜本番運用までをサポートします。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を提供します。

- J-Quants API からの株価・財務・市場カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution レイヤー）スキーマと初期化
- 差分 ETL（バックフィル対応）と品質チェック（quality モジュール）
- ニュース（RSS）収集と記事 → 銘柄紐付け（SSRF 対策・サイズ制限・正規化）
- 研究向けのファクター計算（Momentum / Volatility / Value 等）と特徴量正規化ユーティリティ
- 特徴量生成（feature_engineering）とシグナル生成（signal_generator）の実装（冪等処理）
- 市場カレンダー管理（営業日判定 / next/prev / バッチ更新）
- 発注・監査用スキーマ（audit）や実行レイヤーのテーブル定義

設計上のポイント:
- ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用
- DuckDB によるローカル永続化（冪等保存: INSERT ... ON CONFLICT）
- 外部依存を限定（標準ライブラリ＋最小限の必須パッケージ）
- 自動環境変数読み込み（プロジェクトルートの .env / .env.local）を提供（必要に応じて無効化可）

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（retry/refresh/token キャッシュ/ページネーション）
- data.schema: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
- data.pipeline: ETL ワークフロー（run_daily_etl 等）
- data.news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
- data.calendar_management: JPX カレンダーの管理・営業日判定
- data.stats: zscore_normalize 等の統計ユーティリティ
- research.factor_research: momentum / volatility / value 等のファクター計算
- research.feature_exploration: 将来リターン計算・IC 計算・ファクター統計
- strategy.feature_engineering: 生ファクターを合成・正規化して features テーブルへ保存
- strategy.signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- config: 環境変数管理（自動 .env ロード・必須チェック・環境判定）

---

## セットアップ手順

※ 以下は一般的な手順例です。プロジェクトの pyproject.toml / requirements.txt に従ってください。

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install --upgrade pip
```

3. 依存パッケージをインストール
- 必須（コード中に使用される代表的パッケージ）:
  - duckdb
  - defusedxml
- 例:
```bash
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt / pyproject があれば:
# pip install -e .
```

4. 環境変数の準備
- プロジェクトルート（.git がある親ディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（config モジュールが自動でロードします）。
- 主な必須環境変数:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- オプション:
  - KABUSYS_API_BASE_URL (kabu API ベース URL、デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)
- 自動 .env 読み込みを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # POSIX
set KABUSYS_DISABLE_AUTO_ENV_LOAD=1      # Windows cmd
```

5. DuckDB スキーマ初期化
```python
>>> from kabusys.data.schema import init_schema
>>> conn = init_schema("data/kabusys.duckdb")   # ディレクトリ自動作成
>>> conn.close()
```

---

## 使い方（例）

以下は代表的な操作の Python スニペットです。実稼働前に設定値・テーブルの存在等を確認してください。

- DuckDB 接続の取得（初回は init_schema を使用）
```python
from kabusys.data.schema import init_schema, get_connection

# 初期化（ファイル作成＋テーブル作成）
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量のビルド（features テーブル作成）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（既知銘柄セットを与えて銘柄紐付けを行う）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 研究用機能（IC 計算や forward returns）
```python
from kabusys.research import calc_forward_returns, calc_ic, rank, factor_summary
# prices_daily などが入っている conn を使って処理できます
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

config.Settings を通じてコード内から参照されます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主なファイル）

以下はソースディレクトリ（src/kabusys）の主要ファイル群の一覧（抜粋）です。

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
    - features.py
    - calendar_management.py
    - audit.py
    - audit の関連定義（DDL 等）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/           # 発注／約定管理のための名前空間（将来的な実装）
    - __init__.py
  - monitoring/          # 監視/メトリクス系（将来的な実装）
    - __init__.py

（実際のリポジトリにはさらに doc/ や tests/、scripts/ 等が含まれることがあります）

---

## 開発・テストのヒント

- 自動 .env 読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。テストでこれを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- テスト用にインメモリ DB を使う:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```
- ネットワーク依存部分（jquants_client.fetch_* や news_collector._urlopen 等）はモック可能な設計になっています。ユニットテストでは外部呼び出しをモックして使ってください。
- DuckDB 用 DDL は schema.init_schema() で冪等に作成されます。マイグレーションは現状未実装のため、DDL 更新時は注意してください。

---

## ライセンス・貢献

- ライセンス情報やコントリビューションガイドはリポジトリのトップレベル（LICENSE / CONTRIBUTING.md）を参照してください（本コードベースには記載がないため、適宜追加してください）。

---

この README はコードベースに含まれる実装に基づいて作成しています。運用前に必ず環境変数、API トークン、データベースバックアップ方針、発注フローの安全策（paper_trading での十分な検証）を確認してください。質問や補足のリクエストがあればお知らせください。