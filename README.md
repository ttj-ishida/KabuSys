# KabuSys

日本株向けの自動売買システム基盤（研究・データ基盤・戦略・バックテスト・疑似実行を含む）。  
このリポジトリは、J-Quants API からのデータ取得、ETL、特徴量生成、シグナル生成、バックテストおよびニュース収集までの主要コンポーネントを提供します。

主な設計方針：
- ルックアヘッドバイアスの回避（target_date 時点の情報のみ利用）
- DuckDB を中心としたローカルDB設計（冪等保存・トランザクション）
- 外部API呼び出しに対してレートリミット・リトライ・トークンリフレッシュ対応
- テスト容易性のため依存注入（id_token 注入など）をサポート

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / カレンダー）
  - raw_data の DuckDB への冪等保存（ON CONFLICT 対応）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（quality モジュール想定）
- ニュース収集
  - RSS フィードの取得・前処理・記事保存・銘柄抽出
  - SSRF 対策、受信サイズ制限、XML の安全処理
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターのマージ、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - features + ai_scores 統合 → final_score 計算 → BUY/SELL シグナル生成（売り条件・Bear レジーム対応）
- バックテストフレームワーク
  - ポートフォリオシミュレータ（手数料・スリッページ・全量SELL）
  - 日次ループ、positions の書き戻し、シグナル約定ロジック
  - メトリクス（CAGR / Sharpe / MaxDD / Win Rate / Payoff / Trades）
  - CLI エントリポイントで日付レンジを指定して実行可能
- DB スキーマ管理
  - DuckDB 用のスキーマ定義と init_schema 関数でテーブル作成

---

## 必要条件 / 推奨環境

- Python 3.10+
- duckdb
- defusedxml
- 標準ライブラリ（urllib 等）は多用
- ネットワークアクセス（J-Quants、RSS フィード）を行う場合は適切な API トークンとネットワークが必要

（プロジェクトに requirements.txt がある場合はそちらを使用してください。なければ最低限 duckdb と defusedxml をインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローンして移動
   ```bash
   git clone <このリポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   - もし requirements.txt があれば：
     ```bash
     pip install -r requirements.txt
     ```
   - なければ最低限：
     ```bash
     pip install duckdb defusedxml
     ```
   - 開発インストール（パッケージ化されている場合）：
     ```bash
     pip install -e .
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を配置できます。config モジュールは自動でプロジェクトルートの .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定が必要な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - （任意）SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）

5. DuckDB スキーマの初期化
   Python REPL またはスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可
   conn.close()
   ```

---

## 使い方（主要な例）

### バックテスト（CLI）
DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が事前に用意されている想定です。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

実行後、簡単なメトリクスが標準出力に表示されます。

### DuckDB コネクション取得例
```python
from kabusys.data.schema import init_schema, get_connection

# 新規作成（テーブルを作る）
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続するだけなら
conn2 = get_connection("data/kabusys.duckdb")
```

### 特徴量生成（features を作る）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
conn.close()
```

### シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals written: {n}")
conn.close()
```

### データ ETL（株価の差分 ETL 実行例）
data.pipeline の run_prices_etl を直接呼ぶことで差分取得→保存が可能（J-Quants トークンを settings から利用）。
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
conn.close()
```

### ニュース収集ジョブ（RSS）実行例
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使用する有効コードのセット（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)
conn.close()
```

---

## 主要な環境変数（SUMMARY）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: 通知用 Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

config.Settings を経由してこれらを取得します。必須変数が未設定のときは ValueError が投げられます。

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得＋保存関数）
    - news_collector.py           : RSS ニュース収集・前処理・保存
    - pipeline.py                 : ETL パイプライン（差分取得など）
    - schema.py                   : DuckDB スキーマ定義 / init_schema
    - stats.py                    : zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py          : Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py      : 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py      : features の作成（正規化・ユニバースフィルタ）
    - signal_generator.py         : final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                   : バックテストの全体ループ（run_backtest）
    - metrics.py                  : バックテスト評価指標計算
    - simulator.py                : PortfolioSimulator（約定・評価）
    - clock.py                    : SimulatedClock（将来拡張用）
    - run.py                      : CLI エントリポイント (python -m kabusys.backtest.run)
  - execution/                     : 発注・実行関連（パッケージ領域、詳細未実装箇所あり）
  - monitoring/                    : 監視・メトリクス関連（実装の起点）
- src/kabusys/*.py ほか: 主要機能モジュール

---

## 備考 / 開発者向けメモ

- 多くの処理は DuckDB 接続を受け取り DB を直接操作します。テスト時は ":memory:" を使ったインメモリ接続で高速にテスト可能です。
- jquants_client は内部でレートリミットとリトライ、401 の自動リフレッシュを実装しています。テスト時は get_id_token や _request をモックしてください。
- news_collector は SSRF 対策や受信サイズ制限、defusedxml による安全パースを組み込んでいます。外部リソースを本番環境で扱う際は適切なネットワーク/プロキシ設定を行ってください。
- config._find_project_root は .git または pyproject.toml を探索して .env 自動読み込みを行います。CIやテストで自動読み込みを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要であれば README に以下の追加情報を追記できます：
- 依存パッケージの完全な一覧（requirements.txt から）
- .env.example のテンプレート
- データベーステーブル説明（DataSchema.md などの抜粋）
- 開発 / デプロイ手順（systemd / docker-compose 例）
- テスト実行方法（pytest 等）

追記してほしい項目があれば教えてください。