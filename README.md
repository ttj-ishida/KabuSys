# KabuSys

日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。  
このリポジトリはデータ収集（J-Quants / RSS）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテストシミュレーションなどの機能を含みます。モジュール設計は本番運用（ライブ取引）・ペーパートレード・研究用途のいずれにも対応できるよう分離してあります。

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点までのデータのみ使用）
- DuckDB をデータ格納層に利用（軽量かつ SQL が利用可能）
- バックテストは純粋なメモリ内シミュレータで再現性を確保
- 外部 API からの取得はレート制限・リトライ・トークンリフレッシュを備えた実装

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務情報、上場情報、マーケットカレンダー）
  - RSS ニュース収集（SSRF/サイズ/トラッキング除去対策、記事→銘柄紐付け）
  - DuckDB へ冪等保存（ON CONFLICT でアップデート）

- 研究（research）
  - ファクター計算: momentum / volatility / value（prices_daily / raw_financials を参照）
  - 将来リターン（forward returns）、IC（Spearman）・統計サマリー

- 特徴量エンジニアリング（strategy.feature_engineering）
  - 研究で算出した生ファクターを Z スコア正規化し features テーブルへ保存
  - ユニバースフィルタ（最低株価、平均売買代金）適用

- シグナル生成（strategy.signal_generator）
  - features + AI スコアを統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの保存

- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 等配分・スコア加重（calc_equal_weights / calc_score_weights）
  - リスクに基づくサイジング（calc_position_sizes）
  - セクター集中上限の適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）

- バックテスト（backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - フルバックテストエンジン（run_backtest）
  - メトリクス計算（CAGR / Sharpe / MaxDD / Winrate / Payoff）
  - CLI ラッパー（python -m kabusys.backtest.run）

---

## 前提（Prerequisites）

- Python 3.10 以上（型記法 X | Y を使用しているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）
- その他標準ライブラリ（urllib, logging, math, datetime 等）

推奨パッケージ（requirements.txt の例）:
- duckdb
- defusedxml

（必要に応じて slack_sdk 等を追加してください）

---

## セットアップ手順

1. リポジトリをクローンして開発用環境を作成します。

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# または requirements.txt を用意している場合:
# pip install -r requirements.txt
```

2. 開発モードでインストール（任意）

```bash
pip install -e .
```

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知用 bot token（監視機能などで使用）
- SLACK_CHANNEL_ID — Slack チャネル ID

その他（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

例 `.env`（リポジトリルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

※ .env の読み込みはプロジェクトルート（.git または pyproject.toml を起点）から自動検出します。

---

## 使い方（代表的な操作）

### バックテスト実行（CLI）

事前に DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が用意されている必要があります。スキーマ初期化用のヘルパー関数 init_schema が `kabusys.data.schema` にあります（本 README に全スキーマは含めていません）。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --max-positions 10
```

出力にバックテストの評価指標（CAGR / Sharpe / Max Drawdown / Win Rate 等）が表示されます。

### プログラムからバックテストを呼ぶ

Python スクリプト内から run_backtest を直接呼ぶこともできます。

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema   # スキーマ初期化ユーティリティ
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
conn.close()

print(result.metrics.cagr, result.metrics.sharpe_ratio)
```

### 特徴量構築（build_features）

DuckDB 接続と計算日を渡して features テーブルを構築します。

```python
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
print("upserted features:", count)
conn.close()
```

### シグナル生成（generate_signals）

features / ai_scores / positions を参照して signals テーブルへ書き込みます。

```python
from datetime import date
from kabusys.strategy.signal_generator import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
print("signals generated:", num)
conn.close()
```

### ニュース収集ジョブ（RSS）

RSS をフェッチして raw_news / news_symbols に保存します。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 銘柄コードセット（抽出用）
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

### J-Quants データ取得と保存

J-Quants から日足や財務情報を取得して DuckDB に保存できます。

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print("saved rows:", saved)
conn.close()
```

（認証は `JQUANTS_REFRESH_TOKEN` を参照します）

---

## 主要ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（.env 自動読み込み、settings オブジェクト）
  - data/
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py — RSS 収集・前処理・保存・銘柄抽出
    - (schema.py 等: DuckDB スキーマ初期化/DDL を含む想定)
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — ファクターの正規化・features テーブル生成
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py — 候補選定・等配分/スコア加重
    - position_sizing.py — 株数決定（risk_based 等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストメインループ（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定、history/trades）
    - metrics.py — バックテスト指標計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - execution/ — 実行層（kabu API 等の発注ロジックを配置予定）
  - monitoring/ — 監視・通知関連（Slack 連携等、実装予定）

---

## 設計上の注意点・運用メモ

- ルックアヘッドバイアス対策: features, signals, prices などの処理は target_date 時点で利用可能なデータのみで計算するよう設計されています。バックテストに使用する DB はバックテスト開始日以前に取得されたデータで初期化してください。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に `.env` / `.env.local` を読み込みます。テスト時に自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- レート制限: J-Quants クライアントは 120 req/min を守るための RateLimiter とリトライ機構を実装しています。大量取得時は時間を考慮してください。
- RSS 収集の安全対策: SSRF 対策、応答サイズ上限、gzip 解凍時の再チェック、XML パースの安全化（defusedxml）などを実装しています。

---

## 開発 / 貢献

- コードスタイルや型付けを尊重してプルリクエストをお願いします。
- 新機能や修正の前に issue を立てて設計コンセンサスを取りましょう。
- 単体テストや小さな統合テストを追加してください（duckdb を使ったテストは容易に行えます）。

---

以上がこのコードベースの概要と基本的な使い方です。必要であれば、README に「スキーマ定義」「サンプル .env.example」「requirements.txt の完全版」などを追加で出力します。どの項目を追記しますか？