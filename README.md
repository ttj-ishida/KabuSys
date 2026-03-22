# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集などを含む一貫したワークフローを提供します。

主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB ベースの冪等スキーマ & データ保存
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量正規化（Zスコア）と features テーブルへの保存
- シグナル生成（AI スコア統合、Bear レジーム抑制、BUY/SELL 判定）
- バックテストフレームワーク（ポートフォリオシミュレータ、メトリクス）
- ニュース収集（RSS、SSRF対策、トラッキングパラメータ除去、記事→銘柄紐付け）
- ETL パイプライン用ユーティリティ（差分更新、品質チェック）

以下はコードベースからの抜粋に基づくドキュメントです。

---

## 機能一覧（概要）

- data/
  - jquants_client: J-Quants API 呼び出し・ページネーション・保存（raw_prices/raw_financials/market_calendar）
  - news_collector: RSS 収集、記事正規化、raw_news / news_symbols への保存
  - schema: DuckDB スキーマ定義と init_schema()
  - stats: zscore_normalize 等の統計ユーティリティ
  - pipeline: 差分ETL、日次更新ロジック（ETLResult 等）
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン / IC / ファクターサマリ
- strategy/
  - feature_engineering: build_features(conn, target_date) — ファクターの統合・正規化・features へ UPSERT
  - signal_generator: generate_signals(conn, target_date, ...) — ai_scores と統合して BUY/SELL を signals テーブルへ
- backtest/
  - engine: run_backtest(...) — 本番 DB をコピーして日次ループでシグナル生成→約定→時価評価
  - simulator: PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR、Sharpe、MaxDD 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config.py
  - Settings: 環境変数による設定取得（必須キーを _require で検証）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読み込む。無効化可能）

---

## 必要条件 / 依存関係

- Python 3.10 以上（型ヒントに | を使用しているため）
- 主要な外部パッケージ（例）
  - duckdb
  - defusedxml
- （ネットワークアクセスが必要）J-Quants API の利用にはリフレッシュトークンが必要

プロジェクトの実際の requirements.txt / pyproject.toml をご確認ください。

---

## セットアップ手順

1. リポジトリを取得して virtualenv を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   - 例（pip）:
     ```
     pip install -U pip
     pip install duckdb defusedxml
     # ローカル開発インストール（setup.py/pyproject がある場合）
     pip install -e .
     ```
   - 実際のプロジェクトファイルに従ってインストールしてください（pyproject.toml / requirements.txt が存在する場合はそれを利用）。

3. 環境変数を設定
   - 必須環境変数（config.Settings で _require を使うもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（読み込み順: OS env > .env.local > .env）。
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
   conn.close()
   ```

---

## 使い方（主要ユースケース）

以下は代表的な操作の例です。

1) J-Quants から日足を取得して保存（パターン）
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

2) ニュース収集（RSS）を実行して DB に保存
```python
import duckdb
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを自動で行います
known_codes = {"7203","6758","9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

3) 特徴量作成（features テーブルにアップサート）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,12,31))
print("features upserted:", n)
conn.close()
```

4) シグナル生成（signals テーブルに書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,12,31))
print("signals generated:", count)
conn.close()
```

5) バックテスト（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb
```
- 主要オプション: --slippage, --commission, --max-position-pct
- 実装: run_backtest が本番 DB から必要テーブルをインメモリへコピーして日次ループを実行します。

6) バックテストを Python から実行
```python
from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## 注意点 / 設計上のポイント

- 環境設定は Settings クラス経由で取得します。必須キーが未設定だと ValueError が発生します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアント:
  - API レート制限（120 req/min）を守るため内部でスロットリングしています。
  - 401 を受けた場合はリフレッシュトークンでトークンを自動更新してリトライします。
  - レスポンスのページネーション対応、リトライ（指数バックオフ）実装済み。
- news_collector:
  - SSRF 対策（リダイレクト先のホスト検査、http/https のみ許可）
  - トラッキングパラメータを除去して記事IDを SHA-256 で生成（冪等性）
- 特徴量・シグナル生成:
  - ルックアヘッドバイアスを避けるため target_date 時点までのデータのみを使用
  - 正規化はクロスセクション Z スコアを利用、外れ値は ±3 でクリップ
  - AI スコアが欠損する場合は中立値で補完
- バックテスト:
  - 本番 DB を直接汚さないため、必要テーブルをインメモリ DB にコピーして実行
  - スリッページ/手数料モデルやポジションサイズ制約を再現

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
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
    - run.py (CLI)
  - execution/   (発注関連の実装を配置する想定)
  - monitoring/  (監視・アラート関連)
  - backtest/ (上記)
  - research/ (上記)

（リポジトリの最上位に pyproject.toml / .git / .env.example 等がある想定）

---

## 開発 / テストのヒント

- 単体テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動 env 読み込みを抑制すると安定します。
- news_collector._urlopen や jquants_client._request などは外部通信を行うためモックしやすい設計になっています（テスト時に差し替え可能）。
- DuckDB の ":memory:" を使うとテストでインメモリ DB を素早く作成できます（schema.init_schema(":memory:")）。

---

## ライセンス / コントリビューション

（ここには実際のプロジェクトで使っているライセンスや貢献ワークフローを記載してください。）

---

README はここまでです。必要であれば以下を追加できます：
- API リファレンス（関数・引数の一覧）
- .env.example のテンプレート
- CI / フォーマット / 静的解析ルール（mypy/ruff/black 等）
- 実運用時の運用フロー（ETL スケジューリング、監視、Slack 通知の設定例）