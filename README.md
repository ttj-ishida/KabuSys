# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / 研究フレームワークです。DuckDB を用いたデータ基盤、J-Quants からのデータ収集、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストシミュレータ、ニュース収集などの機能を含みます。設計はルックアヘッドバイアス回避や冪等性（再実行安全性）を重視しています。

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価/財務/カレンダー等、ページネーション・リトライ・トークン自動更新対応）
  - RSS ニュース収集（SSRF対策、トラッキングパラメータ除去、記事ID生成、銘柄紐付け）
  - DuckDB への冪等保存ユーティリティ

- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials ベース）
  - Zスコア正規化、ユニバースフィルタ、features テーブルへの書き込み

- シグナル生成
  - 正規化ファクターと AI スコアを統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの冪等書き込み

- ポートフォリオ構築
  - 候補選定（スコア降順）、等分配／スコア加重／リスクベースのサイジング
  - セクター集中制限、レジーム乗数、単元株丸め、集約キャップ調整

- バックテスト
  - インメモリ DuckDB コピーによる隔離されたバックテスト環境構築
  - 約定シミュレータ（スリッページ、手数料、部分約定、SELL優先）
  - バックテストメトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff 等）
  - CLI からのバックテスト実行（python -m kabusys.backtest.run）

---

## 前提 / 依存

（最小限／代表的なパッケージ）
- Python 3.10+
- duckdb
- defusedxml
- （ネットワークアクセスおよび J-Quants の認証情報）

プロジェクトで使う追加パッケージは環境・デプロイ先に応じて requirements.txt を作成してください。

---

## セットアップ手順（開発用・簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # 開発用: pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化
   - 本リポジトリには schema 初期化関数（kabusys.data.schema.init_schema）を想定しています。DB ファイルを準備し、必要なテーブル（prices_daily, raw_financials, features, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols, positions, signals など）を作成してください。
   - 例: Python から `from kabusys.data.schema import init_schema; conn = init_schema("data/kabusys.duckdb")`

---

## 必須環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、data.jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（monitoring/通知）
- SLACK_CHANNEL_ID: Slack チャネル ID

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方

以下は代表的な利用例です。

1) バックテスト（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb
```
主なオプション:
- --slippage, --commission, --max-position-pct, --allocation-method (equal|score|risk_based), --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

2) Python API 例: 特徴量構築
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

3) Python API 例: シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
# conn は DuckDB 接続（features, ai_scores, positions が整備されていること）
n = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals written: {n}")
```

4) データ収集（J-Quants）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
save_daily_quotes(conn, records)
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
cnts = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(cnts)
```

---

## 開発者向け注意点 / 設計方針（概略）

- ルックアヘッドバイアスを防ぐため、feature/signal の計算は target_date 時点までに利用可能なデータのみを使用します。
- DuckDB への書き込みは基本的に日付単位での削除→挿入を行い、冪等性を確保します。
- J-Quants API ではレート制限を守るため固定間隔レートリミッタとリトライ・トークン自動更新を実装しています。
- バックテストは本番 DB を汚さないよう、インメモリに参照範囲をコピーして実行します。
- ニュース収集は SSRF 対策・レスポンスサイズ制限・XML パースの安全化を行っています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - 環境変数の読み込み・検証（.env 自動ロード、Settings クラス）

- data/
  - jquants_client.py ― J-Quants API クライアント、データ取得・DuckDB 保存ユーティリティ
  - news_collector.py ― RSS 取得・テキスト前処理・raw_news 保存・銘柄抽出
  - （その他 schema, calendar_management 等を想定）

- research/
  - factor_research.py ― Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py ― 将来リターン計算、IC、統計サマリ

- strategy/
  - feature_engineering.py ― features の構築（正規化・フィルタ・DB 書込）
  - signal_generator.py ― final_score 計算、BUY/SELL 生成、signals 書込

- portfolio/
  - portfolio_builder.py ― 候補選定・重み計算
  - position_sizing.py ― 株数算出、キャップ・スケール処理
  - risk_adjustment.py ― セクターキャップ、レジーム乗数

- backtest/
  - engine.py ― バックテスト全体ループ、インメモリデータコピー、発注ロジック
  - simulator.py ― 約定シミュレータ（PortfolioSimulator、TradeRecord、DailySnapshot）
  - metrics.py ― バックテスト評価指標の計算
  - run.py ― CLI エントリポイント

- execution/, monitoring/
  - 実運用の発注・監視関連モジュール（プレースホルダ／実装箇所）

---

## 参考・運用メモ

- 本リポジトリは研究用途からライブ運用までカバーする設計ですが、実運用前に必ずペーパートレード環境で十分な検証を行ってください（KABUSYS_ENV により paper_trading / live を切替可）。
- DuckDB のスキーマ初期化や外部データの ETL（prices_daily / raw_financials / stocks / market_calendar）を事前に整備する必要があります。
- 機微な資金管理・API 認証情報は適切に管理してください（.env をバージョン管理しない等）。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt の候補、より詳細なスキーマ/テーブル定義や API の動作フロー図も作成できます。どの追加情報が欲しいか教えてください。