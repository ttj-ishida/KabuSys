# KabuSys

日本株向けの自動売買システム用ライブラリ / ツール群です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、実行レイヤーなどを含むモジュール構成で、DuckDB をデータストアとして想定しています。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（rate-limit / retry / token refresh 対応）
- DuckDB を用いたデータスキーマと ETL パイプライン
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化・統合（features テーブルへの保存）
- シグナル生成（final_score の計算、BUY/SELL の判定）
- バックテストフレームワーク（ポートフォリオシミュレーション、メトリクス）
- RSS ベースのニュース収集と銘柄紐付け
- 実運用向けの設定管理（環境変数、.env の自動読み込み）

設計方針として「ルックアヘッドバイアスを避ける」「DB への書き込みは冪等（idempotent）」「外部依存は最小限」などが貫かれています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ、DuckDB 保存関数）
  - news_collector: RSS 取得・正規化・DB 保存、銘柄抽出
  - pipeline: 差分取得・ETL ジョブの管理
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- strategy/
  - feature_engineering: raw ファクターを統合して features テーブルへ保存
  - signal_generator: features と ai_scores を統合し BUY/SELL シグナルを生成
- backtest/
  - engine: バックテストの全体ループ（run_backtest）
  - simulator: ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - metrics: バックテスト評価指標計算
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config.py: 環境変数・設定管理（.env 自動ロード、必須チェック）
- execution/: 実運用発注周りのためのプレースホルダ（将来的拡張）

---

## 要件（Prerequisites）

- Python 3.10+
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml

開発環境では setuptools / pip / virtualenv を推奨します。

例（pipenv/venv を用いる簡易手順）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable インストールする場合
pip install -e .
```

（プロジェクト提供の requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール（上記参照）
3. DuckDB の初期スキーマを作成
   - 例:
     ```py
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - あるいは Python セッション内で:
     ```py
     from kabusys.data.schema import init_schema
     init_schema('data/kabusys.duckdb')
     ```

4. 環境変数を設定（以下参照）。プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 環境変数（主要）

config.Settings により参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（代表的な操作例）

以下は代表的な操作の簡易例です。実運用ではログ出力や例外ハンドリングを適宜追加してください。

1) DuckDB スキーマ初期化
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

2) J-Quants からデータを差分取得して保存（ETL）
```py
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema('data/kabusys.duckdb')
# 例: 今日までの差分取得
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched} saved={saved}")
conn.close()
```
（pipeline.run_prices_etl の呼び出し方は引数で date 範囲や backfill を指定できます）

3) ニュース収集（RSS）と銘柄紐付け
```py
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema('data/kabusys.duckdb')
known_codes = {"7203","6758","6954"}  # 事前に有効銘柄コードのセットを準備
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

4) 特徴量の作成（features テーブルへの書き込み）
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema('data/kabusys.duckdb')
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted features: {count}")
conn.close()
```

5) シグナル生成（signals テーブルへの書き込み）
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema('data/kabusys.duckdb')
n = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals generated: {n}")
conn.close()
```

6) バックテスト（CLI）
DuckDB を事前に準備しておき、prices_daily / features / ai_scores / market_regime / market_calendar が揃っていることが前提です。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

7) パッケージをモジュールとして使う（例: バッチジョブや Cron）
- ETL やバックテスト、ニュース収集、feature/signal の呼び出しは全て import して関数を呼ぶ形で利用できます。

---

## ディレクトリ構成（抜粋）

（ソースは `src/kabusys/` 配下）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
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
  - execution/
    - __init__.py
  - monitoring/  (監視・メトリクス関連は別途実装想定)

主要モジュールの役割:
- data/schema.py: DuckDB の DDL と初期化（init_schema）
- data/jquants_client.py: API 取得 + DuckDB 保存関数（save_*）
- data/news_collector.py: RSS 収集・前処理・保存・銘柄抽出
- research/*: ファクター計算・評価用ユーティリティ
- strategy/*: 特徴量作成とシグナル生成ロジック
- backtest/*: バックテストエンジンとシミュレータ

---

## 開発 / テスト / 注意点

- Python 3.10 以降が必要（PEP 604 の `X | Y` 形式などを利用）
- config.py はプロジェクトルートの `.git` または `pyproject.toml` を基準に .env を自動読み込みします。CI やテストで自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマは冪等（存在すれば再作成しない）です。初回のみ init_schema() を呼んでください。
- API 呼び出し（J-Quants）にはレート制御とリトライロジックが組み込まれていますが、API キーやレート制限は外部ルールに従ってください。
- ニュース収集は SSRF・XML 注入・gzip bomb などに対する防御ロジックを含みますが、公開環境ではさらに監査と上限設定を行ってください。

---

## 参考・今後の拡張

- execution レイヤーの実装（kabuステーションとの連携）や Slack 通知の実装は別途追加可能です。
- AI スコア（ai_scores）の生成・学習パイプラインは外部プロセスに依存する想定です。strategy.signal_generator は ai_scores を参照して統合します。
- tests/ や CI 設定、requirements の固定化（pip freeze / pyproject.toml）を追加してください。

---

何か追加したいセクション（例: API リファレンス、ユースケース別のワークフロー、運用チェックリストなど）があれば教えてください。README を用途に合わせて拡張します。