# KabuSys

日本株自動売買システムのライブラリ / フレームワーク群です。データ収集（J-Quants 等）→ ETL → 特徴量生成 → シグナル生成 → バックテスト / 実行、という一連のワークフローを提供します。設計はルックアヘッドバイアス防止・冪等性・テスト容易性を重視しています。

---

## 概要

KabuSys は以下のレイヤーを持つモジュール群です。

- data: J-Quants クライアント、RSS ニュース収集、DuckDB スキーマ/ETL、統計ユーティリティ
- research: ファクター計算・特徴量探索ツール（バックテスト用のデータ準備）
- strategy: 特徴量の正規化・合成（feature_engineering）とシグナル生成（signal_generator）
- backtest: ポートフォリオシミュレータ、バックテストエンジン、メトリクス計算、CLI
- execution / monitoring: 実行・監視のための構成（現状は層の準備）
- config: 環境変数・設定管理（.env 自動読み込み等）

設計上の要点:
- DuckDB をデータベースとして利用
- ETL・保存処理は冪等（ON CONFLICT / トランザクション）で実装
- J-Quants API はリトライ・レート制御・トークン自動更新に対応
- ニュース収集は SSRF/サイズ上限/XML セキュリティ考慮
- ルックアヘッドバイアスの排除（target_date 時点のデータのみ参照）

---

## 主な機能一覧

- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・市場カレンダーの取得（ページネーション対応）
  - レートリミット制御、リトライ、IDトークン自動更新
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_prices_etl 等（差分更新と品質チェックをサポート）

- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化、記事 ID 生成、raw_news への保存、銘柄抽出

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）

- 研究（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ

- 戦略（strategy）
  - build_features: 生ファクターの正規化・合成、features テーブルへの UPSERT
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成、signals テーブルへ保存

- バックテスト（backtest）
  - PortfolioSimulator（約定・スリッページ・手数料モデル）
  - run_backtest: 本番 DB からインメモリにデータをコピーして日次シミュレーションを実行
  - メトリクス計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）

---

## セットアップ手順（開発環境）

1. Python 環境を準備（推奨: 3.9+）

2. 仮想環境の作成と有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 本リポジトリの実際の requirements.txt があればそれを使用してください。最低限必要なライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （注: ライブラリは将来的に増える可能性があります。プロジェクトの requirements.txt がある場合はそちらを使用してください。）

4. プロジェクトをパスに追加（開発インストール）
   - pip install -e .

5. DuckDB スキーマ初期化（例）
   - Python REPL / スクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - デフォルトの DuckDB パスは settings.duckdb_path のデフォルト "data/kabusys.duckdb" です。

---

## 環境変数 / 設定

KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（CWD ではなくパッケージファイル位置から .git または pyproject.toml を探索）。自動読み込みを停止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu API 用パスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

任意（デフォルト有り）:
- KABUSYS_ENV: 開発環境を指定（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパスデフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パスデフォルト: data/monitoring.db

settings は kabusys.config.settings から取得可能です。

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=yourpassword
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

### DuckDB スキーマの初期化

Python から:
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: でも可
conn.close()
```

### J-Quants からデータ取得 → 保存（例）

```
from datetime import date
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
conn.close()
```

### 特徴量生成

DuckDB 接続を渡して指定日分の features を構築します。

```
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,2,28))
print(f"features upserted: {n}")
conn.close()
```

### シグナル生成

```
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,2,28))
print(f"signals written: {count}")
conn.close()
```

weights を上書きして呼ぶことも可能:
```
weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.15, "liquidity": 0.1, "news": 0.05}
generate_signals(conn, date(2024,2,28), weights=weights)
```

### バックテスト CLI

モジュールとして実行可能なエントリポイントがあります。

例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```

主要オプション:
- --start / --end: バックテスト期間（YYYY-MM-DD）
- --db: DuckDB ファイルパス
- --cash: 初期資金（JPY）
- --slippage, --commission, --max-position-pct: シミュレーションパラメータ

また Python API で run_backtest を直接呼べます:
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
print(result.metrics)
conn.close()
```

---

## 主要モジュールの説明 / ディレクトリ構成

（主要なファイル・ディレクトリの概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須キーチェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・レート制御・リトライ）
    - news_collector.py
      - RSS 収集、前処理、raw_news/news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（差分更新など）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（ファクター正規化→features へ UPSERT）
    - signal_generator.py
      - generate_signals（final_score 計算、BUY/SELL 判定→signals へ保存）
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（本番 DB をインメモリにコピーして日次ループを実行）
    - simulator.py
      - PortfolioSimulator, DailySnapshot, TradeRecord（約定・時価評価）
    - metrics.py
      - バックテスト指標計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
    - run.py
      - CLI エントリポイント
    - clock.py
      - SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （発注/実行層の実装用エンドポイントを配置）
  - monitoring/
    - （監視・メトリクス収集用のモジュール置き場）

上記以外にもユーティリティや補助モジュール（quality チェック等）が含まれます。

---

## 実運用上の注意点

- 環境変数に機密情報（トークン / パスワード）を含めるため、リポジトリに .env を置かないことを推奨します。
- J-Quants の API レートリミット・利用規約を遵守してください。
- 実口座（live）環境では十分なテスト（paper_trading）を経てください（settings.is_live / is_paper を利用）。
- DuckDB のファイルは適切にバックアップしてください。
- ニュース収集は外部 HTTP を多用するためネットワークやセキュリティに注意してください。

---

## 開発貢献について（簡易）

1. Issue を立てる（バグ / 機能提案）
2. ブランチを切る、変更を実装
3. テストとローカルでの動作確認
4. Pull Request を送る（変更点・理由を明記）

---

この README はリポジトリ内の現状のコード（strategy、research、data、backtest 等）に基づいて作成しています。追加で README に含めたい情報（例: 実行例の具体的な SQL スキーマ、CI 設定、requirements.txt）や翻訳調整があれば教えてください。