# KabuSys

日本株向けの自動売買 / バックテスト / データパイプライン用ライブラリ。  
ファクター計算・特徴量構築・シグナル生成・ポートフォリオ構築・バックテストシミュレータ・ニュース収集などを含むモジュール群を提供します。

バージョン: 0.1.0

## 概要
KabuSys は以下を目的とした研究および運用支援ライブラリです。

- DuckDB を使った時系列データ管理とファクター計算
- 特徴量の正規化・統合と売買シグナル生成
- ポートフォリオ構築（候補選定・配分・リスク調整・単元丸め）
- バックテスト（擬似約定・スリッページ・手数料を考慮）
- ニュース収集（RSS）と記事 → 銘柄紐付け
- J-Quants API クライアントによるマーケットデータ取得

設計上、ルックアヘッドバイアス回避、冪等性、明示的なデータフェッチ/保存、テスト容易性を重視しています。

## 主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（fetch / save: 日足・財務・上場情報・カレンダー）
  - ニュース RSS 収集と DB 保存（SSRF/サイズ制限/トラッキングパラメータ除去）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - IC（スピアマン）や将来リターンの計算、統計サマリ
- 特徴量構築 & シグナル生成
  - features テーブルへの Z スコア正規化・クリップ
  - AI スコアと統合した final_score に基づく BUY/SELL シグナル生成
  - Bear レジームでの BUY 抑制、SELL のストップロス判定
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額/スコア加重/リスクベースのサイジング
  - セクター集中制限、レジーム乗数適用、単元丸め
- バックテスト
  - インメモリ DuckDB コピーで安全にバックテスト実行
  - 擬似約定ロジック（部分約定・手数料・スリッページ）
  - 日次スナップショット、トレード記録、評価指標（CAGR、Sharpe、MaxDD 等）
  - CLI ランナー（python -m kabusys.backtest.run）
  
## 必要条件（環境）
- Python 3.10 以上（Union 型記法 Path | None 等を使用）
- 必須パッケージ（主要な依存）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, logging, datetime, math 等）

pip の requirements ファイルはプロジェクトに含めてください（例示: duckdb, defusedxml）。

## セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   例（最低限）:
   ```
   pip install duckdb defusedxml
   ```
   開発用にパッケージを一括でインストールする場合は requirements.txt を用意して:
   ```
   pip install -r requirements.txt
   ```

4. パッケージをローカルにインストール（editable）
   ```
   pip install -e .
   ```

## 環境変数 / .env
プロジェクトは .env / .env.local / OS 環境変数から設定を自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。重要な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

簡単な .env 例（プロジェクトルートに置く）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## データベース準備
バックテストや多くの処理は DuckDB を前提とします。バックテスト CLI には事前に DB をデータで埋める必要があります（prices_daily, features, ai_scores, market_regime, market_calendar 等）。スキーマ初期化関数は kabusys.data.schema.init_schema を使用します（プロジェクト内の schema 定義に従ってください）。

例（DuckDB ファイル初期化、架空）:
```py
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ここでデータ取り込み処理を実行（J-Quants から取得→保存 等）
conn.close()
```

注意: run_backtest の README 内記載の通り、バックテストに必要なテーブルが揃っていることを確認してください。

## 使い方

### バックテスト CLI
プロジェクトにインストール後、下記コマンドでバックテストを実行できます（例）:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

主なオプション:
- --start / --end : 開始/終了日（YYYY-MM-DD）
- --cash : 初期資金
- --slippage : スリッページ率（デフォルト 0.001）
- --commission : 手数料率（デフォルト 0.00055）
- --allocation-method : equal | score | risk_based（デフォルト risk_based）
- --max-positions : 最大保有数（デフォルト 10）
- --lot-size : 単元株数（デフォルト 100）
- --db : DuckDB ファイルパス（必須）

実行後、CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades が表示されます。

### プログラム API（主要例）
- 特徴量構築
```py
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"{n} 銘柄を features に保存しました")
conn.close()
```

- シグナル生成
```py
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"{count} シグナルを書き込みました")
conn.close()
```

- ニュース収集（RSS）
```py
import duckdb
from kabusys.data.news_collector import run_news_collection

conn = duckdb.connect("data/kabusys.duckdb")
results = run_news_collection(conn)
print(results)  # {source_name: 新規件数}
conn.close()
```

- J-Quants データ取得 & 保存
```py
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, recs)
conn.close()
```
fetch 系は JQUANTS_REFRESH_TOKEN が必要です。

### バックテスト API（プログラム呼び出し）
run_backtest は詳細なパラメータを受け取ります。使用例:
```py
from datetime import date
import duckdb
from kabusys.backtest.engine import run_backtest

conn = duckdb.connect("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
print(res.metrics)
conn.close()
```

## モジュール / ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（自動 .env ロード機能含む）
  - data/
    - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py : RSS 取得・正規化・DB 保存、銘柄抽出
    - (schema.py, calendar_management などが別途存在する想定)
  - research/
    - factor_research.py : Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py : 将来リターン・IC・統計サマリ
  - strategy/
    - feature_engineering.py : features テーブル構築（正規化・UPSERT）
    - signal_generator.py : final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py : 候補選定・重み付け
    - position_sizing.py : 株数決定・aggregate cap ロジック
    - risk_adjustment.py : セクター制限・レジーム乗数
  - backtest/
    - engine.py : バックテスト全体ループ（run_backtest）
    - simulator.py : 擬似約定・ポートフォリオ管理（PortfolioSimulator）
    - metrics.py : バックテスト評価指標計算
    - run.py : CLI エントリポイント
  - portfolio/、strategy/、research/、data/、backtest/ はそれぞれ上記の責務に対応
  - execution/、monitoring/ : 実運用連携・監視ロジック用（スケルトン/拡張対象）

## 設計上の注意点 / ヒント
- ルックアヘッドバイアスを避けるため、計算・シグナル生成は target_date 時点で利用可能なデータのみを参照します。
- J-Quants API はレート制限およびトークン更新ロジックを内蔵しています。API エラー時は自動リトライと指数バックオフを行います。
- ニュース収集は URL 正規化、SSRF 対策、応答サイズ制限を備えています。
- バックテストは本番 DB を直接汚染しないためにインメモリの DuckDB に必要なテーブルをコピーして実行します。

## 貢献 / 変更
- バグ報告、機能提案は issue を立ててください。プルリクエスト歓迎です。
- 主要ロジックはユニットテストしやすい純粋関数・DB 接続分離を意識して実装されています。変更時は関連ユニットテストを追加してください。

---

README はコードの説明と使い方の導線を主に記載しました。実運用に移す際は .env の取り扱いやシークレット管理（Vault 等）の導入、監視・リカバリ設計を追加で行ってください。必要であればサンプル .env.example や schema 初期化手順の詳細を追補できます。