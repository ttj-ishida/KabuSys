# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究プラットフォームです。DuckDB をデータ層に利用し、ファクター計算 → 特徴量構築 → シグナル生成 → サイジング → バックテスト の一連のワークフローを提供します。J-Quants API からのデータ取得や RSS ベースのニュース収集、バックテスト用のポートフォリオシミュレータなどを含むモジュール群で構成されています。

## 主な特徴
- 研究（research）モジュールによるファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量構築（feature_engineering）→ 正規化済み features テーブルの作成
- シグナル生成（signal_generator）: ファクター + AI スコア統合による BUY/SELL シグナル
- ポートフォリオ構築（portfolio）: 候補選定、重み付け、ポジションサイジング、セクター制限、レジーム乗数
- バックテストフレームワーク: 日次ループ、擬似約定、メトリクス計算
- データ取得: J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
- ニュース収集: RSS フィード収集、前処理、記事→銘柄紐付け、DuckDB への冪等保存
- 安全対策: RSS の SSRF 対策、XML の防御、リクエスト上限、トラッキングパラメータ除去 等

---

## 環境変数 / 設定
設定は環境変数（またはプロジェクトルートの `.env`, `.env.local`）から読み込みます。自動ロードはデフォルトで有効です（自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須となる主な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 投稿先チャンネル ID（必須）

任意 / デフォルトがあるもの:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env ファイルのパースはシェル形式（export を含む行、クォート、コメント等）に対応しています。

---

## 前提（依存関係）
- Python 3.10 以上（typing の | アノテーション等を使用）
- duckdb
- defusedxml
- （標準ライブラリのみで動く箇所も多いですが、実行には上記が必要です）

インストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# もしパッケージ化されていれば:
# pip install -e .
```

（requirements.txt がある場合はそれを使用してください。）

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境作成 & 依存パッケージをインストール
3. プロジェクトルートに `.env` を作成（`.env.example` を参照）
4. DuckDB スキーマを初期化／データ投入（ETL スクリプトや別途提供の SQL を使用）
5. 必要に応じて J-Quants API / RSS の収集を行いデータを蓄積

注意: config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env`/.env.local を読み込みます。テストや一時的に自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要な実行例）

### バックテスト（CLI）
バックテストはモジュール化されており、提供されている CLI エントリポイントを使って実行できます。

例:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --lot-size 100
```

主なオプション:
- --start / --end: バックテスト期間
- --db: DuckDB ファイルパス（あらかじめ prices_daily, features, ai_scores, market_regime, market_calendar 等が整備されている必要あり）
- --cash: 初期資金
- --slippage / --commission: コストモデル
- --allocation-method: equal | score | risk_based

バックテストの中核は `kabusys.backtest.engine.run_backtest()` で、戻り値として履歴・約定履歴・評価指標を得られます。

### 特徴量構築（プログラム的利用）
DuckDB 接続を渡して日付単位で features を作成します。

例（Python）:
```python
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2023, 12, 31))
print("upserted:", count)
conn.close()
```

### シグナル生成（プログラム的利用）
features / ai_scores / positions を参照して signals テーブルに BUY/SELL を書き込みます。

例:
```python
from kabusys.strategy.signal_generator import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2023, 12, 31))
print("signals written:", n)
conn.close()
```

### J-Quants データ取得・保存
J-Quants API から日足や財務データを取得して DuckDB に保存するユーティリティを提供します。自動的にトークン更新やレート制限・リトライを行います。

例（日足取得→保存）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print("saved raw prices:", saved)
conn.close()
```

### ニュース収集
RSS から記事を収集し raw_news / news_symbols に保存するジョブを提供します（SSRF・XML 攻撃対策あり）。

例:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(res)
conn.close()
```

---

## よく使う API（概要）
- kabusys.config.settings — 環境変数経由での設定取得
- kabusys.data.jquants_client — J-Quants API クライアント（fetch_ / save_ 関数群）
- kabusys.data.news_collector — RSS 取得・前処理・保存
- kabusys.research.* — ファクター計算（calc_momentum / calc_volatility / calc_value）
- kabusys.strategy.feature_engineering.build_features — features テーブル作成
- kabusys.strategy.signal_generator.generate_signals — signals 作成
- kabusys.portfolio.* — 候補選定 / 重み計算 / サイジング / セクター制限 / レジーム乗数
- kabusys.backtest.run_backtest（および CLI） — バックテスト全体実行
- kabusys.backtest.simulator.PortfolioSimulator — 擬似約定 / マークトゥマーケット / 履歴記録
- kabusys.backtest.metrics.calc_metrics — バックテストの評価指標計算

---

## ディレクトリ構成（概要）
以下は主要ファイル／パッケージ構成の抜粋です（src/kabusys 配下）:

- __init__.py — パッケージメタ情報（version 等）
- config.py — 環境変数 / .env ロード / Settings クラス
- data/
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 収集・記事保存・銘柄抽出
  - (その他: schema / calendar_management / stats 等を想定)
- research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — IC / forward returns / summary 等
- strategy/
  - feature_engineering.py — features 作成処理
  - signal_generator.py — final_score 計算と BUY/SELL 生成
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算（リスクベース / 等配分 等）
  - risk_adjustment.py — セクター制限・レジーム乗数
- backtest/
  - engine.py — バックテストエンジン（メインループ）
  - simulator.py — 擬似約定・PortfolioSimulator
  - metrics.py — バックテスト評価指標
  - run.py — CLI エントリポイント
  - clock.py — （将来用の）模擬時計
- execution/ — 実際の注文送出（空ディレクトリ／実装想定）
- monitoring/ — 監視・メトリクス・Slack 通知（実装想定）

（各モジュールは README の説明を参考にして、目的別に分割されています。コード内の docstring に詳細が記載されています。）

---

## 開発 / テストのヒント
- 自動で .env を読み込みますが、ユニットテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して外部環境を固定化してください。
- DuckDB のインメモリスキーマ（init_schema(":memory:")）を使えば外部ファイルに依存せず高速にテスト可能です。
- RSS 取得や外部 API 呼び出しはモックしやすいように内部関数（例: _urlopen、_request）を切り出しています。

---

## ライセンス / 貢献
（ここにはプロジェクトのライセンスと貢献ガイドを記載してください。リポジトリに LICENSE ファイルがあれば参照を入れてください。）

---

README はコードの実装に合わせて随時更新してください。モジュール毎の詳細な使用例や DB スキーマ（schema.py で定義されているテーブル構成）については該当ソースの docstring を参照してください。