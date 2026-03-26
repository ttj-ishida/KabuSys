# KabuSys

日本株向けの自動売買／バックテストおよびデータパイプライン用ライブラリです。  
ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテストシミュレータ・データ取り込み（J-Quants）・ニュース収集など、研究〜運用に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF / Gzip 対策、トラッキングパラメータ除去）
  - DuckDB への冪等保存（ON CONFLICT を利用）

- 研究 / ファクター
  - Momentum / Volatility / Value 等の定量ファクター計算（DuckDB を使用）
  - 特徴量（features）構築、Zスコア正規化とクリッピング
  - ファクター探索（IC、forward returns、統計サマリ）

- 戦略
  - 特徴量 + AI スコア統合によるシグナル生成（BUY / SELL 判定、ベアレジーム抑制）
  - ポートフォリオ候補選定、等配分／スコア配分、リスクベースのサイジング
  - セクター集中制限、レジーム乗数

- バックテスト
  - 約定モデル（スリッページ・手数料・単元丸め）
  - 日次スナップショット / トレード記録の生成
  - 各種メトリクス（CAGR、Sharpe、Max DD、勝率、Payoff ratio）
  - CLI でのバックテスト実行

- 運用補助
  - 環境変数/設定管理（.env 自動ロード／保護）
  - Slack 連携等の設定用プロパティ（設定は環境変数経由）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに `X | Y` を使用しているため）
- pip などでパッケージをインストール可能な環境

推奨インストール（開発環境）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 依存ライブラリをインストール
   - 必須（コード参照）例: duckdb, defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

環境変数
- 必須（Settings クラスで _require されるもの）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu ステーション API パスワード
  - SLACK_BOT_TOKEN: Slack ボットトークン
  - SLACK_CHANNEL_ID: 通知先チャンネル ID

- 任意 / デフォルト
  - KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

.env 自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local の順に自動で読み込みます。
- 自動ロードを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

例: .env（必須キーのみ）
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要ワークフロー）

以下は代表的な利用例・コマンド例です。詳細は各モジュールを参照してください。

1) バックテスト（CLI）
- 必要条件: DuckDB ファイルが prices_daily / features / ai_scores / market_regime / market_calendar 等を含むこと
- 実行例:
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb
  ```
- オプション: slippage, commission, allocation-method (equal|score|risk_based), max-positions, lot-size 等

2) プログラムからバックテスト実行（API）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema  # schema モジュールで DB を開く想定
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023,1,1),
    end_date=date(2023,12,31),
    initial_cash=10_000_000,
)
conn.close()

# result.history / result.trades / result.metrics を参照
```

3) 特徴量構築（features）
```python
import duckdb
from datetime import date
from kabusys.strategy import build_features

conn = duckdb.connect("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
conn.close()
```

4) シグナル生成
```python
import duckdb
from datetime import date
from kabusys.strategy import generate_signals

conn = duckdb.connect("path/to/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,1,31))
conn.close()
```

5) ニュース収集
```python
import duckdb
from kabusys.data.news_collector import run_news_collection

conn = duckdb.connect("path/to/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # stocks テーブルなどから取得する想定
results = run_news_collection(conn, known_codes=known_codes)
conn.close()
# results はソースごとの新規保存数の辞書
```

6) J-Quants データ取得（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from datetime import date

conn = duckdb.connect("path/to/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
count = save_daily_quotes(conn, recs)
conn.close()
```

注意
- run_backtest の内部ループは positions テーブルを使って SELL 判定を行うため、バックテスト用 DB をあらかじめ整備しておく必要があります。
- J-Quants API はレート制限（120 req/min）・401 自動リフレッシュ・リトライ実装があります。API トークンは環境変数経由で設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys/` の主な構成と各ファイルの目的（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード・必須キー検証）
  - data/
    - jquants_client.py
      - J-Quants API クライアント（取得・保存）
    - news_collector.py
      - RSS ニュース収集・前処理・DB 保存・銘柄抽出
    - (その他: schema, stats, calendar_management 等が想定)
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - IC / forward returns / 統計サマリ等
  - strategy/
    - feature_engineering.py
      - 特徴量（features）構築、正規化、DB への upsert
    - signal_generator.py
      - features と ai_scores を統合して BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py
      - 候補選定・配分重み計算（選定、等配分、スコア配分）
    - position_sizing.py
      - 株数算出（等配分／スコア／リスクベース）、単元丸め、aggregate cap
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - backtest/
    - engine.py
      - バックテスト全体ループ・ヘルパー
    - simulator.py
      - 約定モデル・ポートフォリオ状態管理（PortfolioSimulator）
    - metrics.py
      - バックテスト評価指標
    - run.py
      - CLI エントリポイント
    - clock.py
      - 将来用途の模擬時計
  - portfolio/ (パッケージ __init__ で主要関数をエクスポート)
  - strategy/ (同上)

上記以外にも monitoring, execution などのサブパッケージが想定されており、パッケージ初期化で主要 API を公開しています。

---

## 開発・運用に関する注意点

- Python バージョン: 3.10 以上を想定（型ヒントの union 演算子 `|` を使用）
- DuckDB をデータ永続化／分析用に利用しています。大規模なデータ取得時は I/O とメモリに注意してください。
- ニュース収集モジュールは外部 RSS を取得するためネットワークとセキュリティ（SSRF）対策を組み込んでいますが、運用環境のネットワークポリシーに合わせて確認してください。
- 本コードは研究・バックテスト用に設計されています。実際の売買執行（ライブ運用）する場合は、リスク管理・接続周り・認証周りを十分に検討してください。

---

もし README に追加したい具体的な情報（依存パッケージ一覧、CI / テスト実行方法、.env.example の完全なテンプレートなど）があれば教えてください。必要に応じて追記します。