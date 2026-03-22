# KabuSys

日本株向けの自動売買 / 研究プラットフォーム。  
DuckDB をデータストアとして用い、データ取り込み（J-Quants）、特徴量生成、シグナル生成、バックテスト、ニュース収集などの機能を備えています。

---

## 主要機能（概要）
- データ取得・保存
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを取得して DuckDB に冪等保存（retry / rate-limit / トークン自動リフレッシュ対応）
  - RSS からニュースを収集して raw_news / news_symbols に保存（SSRF/サイズ制限/トラッキングパラメータ除去）
- データパイプライン（ETL）
  - 差分更新・バックフィル対応、品質チェックのフックを備えた ETL（run_prices_etl 等）
- 研究用ファクター計算
  - Momentum / Volatility / Value などのファクターを DuckDB 上で計算
  - ファクター探索（forward returns, IC, summary）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング / シグナル生成（戦略）
  - features テーブル構築（ユニバースフィルタ、Z スコア正規化、クリップ）
  - ai_scores と統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込み
  - Bear レジーム検知、ストップロス等のエグジット判定
- バックテスト
  - 日次シミュレータ（スリッページ・手数料モデル）、ポートフォリオ状態管理
  - run_backtest による履歴生成、トレード記録、各種評価指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio）
- データスキーマ管理
  - DuckDB のスキーマ初期化（init_schema）と接続ユーティリティ

---

## 要件
- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- そのほか標準ライブラリのみ（多くの処理は外部ライブラリに依存しない設計）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

※パッケージ配布用に setup / pyproject があれば `pip install -e .` を使えます。

---

## セットアップ手順

1. リポジトリをクローン／作業ディレクトリに配置
2. 仮想環境を作成して依存ライブラリをインストール（上記参照）
3. DuckDB スキーマ初期化（デフォルトの DB パスは `data/kabusys.duckdb` を想定）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
4. 環境変数設定 (.env を推奨)
   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（少なくとも J-Quants API を使う場合）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabu API 用パスワード（発注を行う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - その他（デフォルトあり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: DB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
```

---

## 使い方（代表的な操作例）

事前に `init_schema()` でスキーマを作成し、環境変数を設定してください。

1) J-Quants からデータを取得して保存（例: 株価）
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

2) ETL（差分取得）例（run_prices_etl を使う）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
target = date.today()
fetched, saved = run_prices_etl(conn, target_date=target)
print(f"fetched={fetched}, saved={saved}")
conn.close()
```

3) 特徴量（features）構築
```python
import duckdb
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,8,1))
print("features upserted:", n)
conn.close()
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,8,1))
print("signals written:", count)
conn.close()
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出対象の銘柄コードセット（例: 上場銘柄の4桁コード集合）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(results)
conn.close()
```

6) バックテスト（CLI）
本リポジトリ内のバックテストエントリポイントを使う方法:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
実行結果として主要指標（CAGR, Sharpe, Max Drawdown 等）が表示されます。

---

## 設計上の注意・動作方針
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点までのデータのみを参照する設計です。
- DB への保存は可能な限り冪等（ON CONFLICT / DO UPDATE）になっており、差分更新・再実行に耐えられます。
- J-Quants クライアントは固定間隔レート制限、リトライ、トークン自動リフレッシュに対応しています。
- ニュース収集は SSRF 対策・レスポンスサイズ制限を実装しています。

---

## ディレクトリ構成（主要ファイル）
以下はソースルート `src/kabusys/` の主要ファイル一覧（抜粋）:

- kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント + 保存関数
    - news_collector.py          # RSS ニュース収集・保存
    - pipeline.py                # ETL パイプライン（差分更新等）
    - schema.py                  # DuckDB スキーマ定義・初期化
    - stats.py                   # 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py         # Momentum/Volatility/Value の算出
    - feature_exploration.py     # forward returns, IC, summary
  - strategy/
    - __init__.py
    - feature_engineering.py     # features テーブル構築
    - signal_generator.py        # final_score 計算・signals 書き込み
  - backtest/
    - __init__.py
    - engine.py                  # run_backtest の実装
    - simulator.py               # PortfolioSimulator
    - metrics.py                 # バックテスト指標計算
    - run.py                     # CLI エントリポイント
    - clock.py
  - execution/                    # 発注実装（初期ファイルのみ）
  - monitoring/                   # 監視関連（実装ファイルがあれば配置）

---

## 開発メモ
- 自動環境変数ロードは config.py により行われ、プロジェクトルートの `.env` / `.env.local` を読み込みます。テストや特殊な状況で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 型ヒントは Python 3.10 の新しい Union 演算子（|）を使用しているため、Python 3.10 以上を推奨します。
- データベーススキーマは DuckDB を想定しています。初回実行前に `init_schema()` を呼んでテーブルを作成してください。
- 大きな外部通信（API / RSS）はタイムアウト・リトライ・サイズ上限が設定されています。実運用ではネットワーク・認証情報の管理に注意してください。

---

必要であれば、README に次の内容も追加できます：
- API の詳細（J-Quants のエンドポイント別使い方）
- ETL のスケジュール例（cron / Airflow）
- 実稼働時の運用手順（ログ・監視・Slack 通知）
- テスト・CI の設定例

追加希望があれば教えてください。