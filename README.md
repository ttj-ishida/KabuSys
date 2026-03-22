# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集などのモジュールを含み、DuckDB をデータレイヤーとして利用する設計です。

主な設計方針：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- DuckDB を用いたローカル DB（ファイル or in-memory）
- 各保存処理は冪等（ON CONFLICT / トランザクション）で実装
- 外部API 呼出しは rate limiting / retry / token refresh を備え安全に実行

---

## 機能一覧

- data/
  - J-Quants API クライアント（jquants_client）
    - 日足データ、財務データ、マーケットカレンダー取得・保存
    - レートリミット制御、指数バックオフ、トークン自動リフレッシュ
  - ニュース収集（news_collector）
    - RSS 取得、テキスト前処理、記事 ID 正規化、銘柄抽出、DB 保存
    - SSRF / XML 攻撃対策、受信サイズ制限
  - ETL パイプライン（pipeline）
    - 差分取得、バックフィル、品質チェックフック
  - スキーマ初期化（schema）
    - DuckDB のテーブル定義と初期化（raw / processed / feature / execution 層）
  - 統計ユーティリティ（stats）
    - Z スコア正規化 等
- research/
  - ファクター計算（factor_research）
    - Momentum / Volatility / Value 等
  - 特徴量探索（feature_exploration）
    - 将来リターン計算、IC（Spearman）、統計サマリ
- strategy/
  - 特徴量生成（feature_engineering）
    - research による生ファクターを正規化して features テーブルへ保存
  - シグナル生成（signal_generator）
    - features / ai_scores を統合、final_score 計算、BUY/SELL シグナルを signals に保存
- backtest/
  - バックテストエンジン（engine）
    - 本番 DB から in-memory DuckDB へデータをコピーし日次ループでシミュレーション
  - ポートフォリオシミュレータ（simulator）
    - 擬似約定（スリッページ・手数料）、日次評価、トレード記録
  - メトリクス（metrics）
    - CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio 等
  - CLI ランナー（run）
    - python -m kabusys.backtest.run でバックテストを実行
- config.py
  - 環境変数読み込み（.env / .env.local 自動読み込み、無効化フラグあり）
  - 必須設定のラップ（settings オブジェクト）

---

## 必要条件 / インストール

- Python 3.10+
  - 型ヒントで `X | None` 構文を使用しているため Python 3.10 以降を想定しています。
- pip で次をインストールしてください（プロジェクトの要件ファイルがある場合はそちらを使用）:

例（最低パッケージ）:
```
pip install duckdb defusedxml
```

開発時にパッケージとして使う場合:
```
pip install -e .
```
（プロジェクトが packaging を提供している前提です）

---

## 環境変数（設定）

config.Settings が以下の環境変数を参照します。必須のものは起動前に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト INFO）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` および `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（最小手順）

1. Python と依存パッケージをインストール
2. 環境変数を設定（.env/.env.local など）
3. DuckDB スキーマを初期化
   ```python
   # Python コンソールまたはスクリプトで
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   またはコマンドで（例）:
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（代表的なワークフロー）

以下はよく使う操作のサンプル。

1) J-Quants からデータ取得・保存（ETL の一部）
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
conn.close()
```

2) ETL: 差分株価 ETL（pipeline 例）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
conn.close()
print(f"fetched={fetched}, saved={saved}")
```

3) 特徴量生成（feature_engineering.build_features）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print("features upserted:", n)
conn.close()
```

4) シグナル生成（strategy.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
print("signals written:", total)
conn.close()
```

5) ニュース収集（news_collector.run_news_collection）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を与えると記事と銘柄の紐付けも行う
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
conn.close()
```

6) バックテスト（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

バックテストは内部で本番 DB から in-memory DuckDB に必要テーブルをコピーし、generate_signals を用いて日次シミュレーションを実行します。

---

## ディレクトリ構成

（src/ を起点とした主要ファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
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
    - clock.py
    - run.py
  - execution/          (発注/実行層、パッケージ存在)
  - monitoring/         (モニタリング層、パッケージ存在)
  - (その他: モジュール単位でユーティリティや DB 操作が分離されています)

---

## 実装上の注意 / トラブルシューティング

- 環境変数未設定で必須値が呼ばれると ValueError が発生します（settings._require でチェック）。.env を準備してください。
- DuckDB のファイルパスは既定で data/kabusys.duckdb です。init_schema は親ディレクトリを自動作成します。
- J-Quants API はレート制限があるため大量リクエスト時は _MIN_INTERVAL_SEC に従ってスロットリングされます。fetch 系関数はページネーション対応です。
- news_collector は RSS のリダイレクト先の検査や圧縮サイズチェック等を行います。ネットワーク例外は呼び出し元でハンドリングしてください。
- バックテスト実行前に prices_daily / features / ai_scores / market_regime / market_calendar が適切に用意されている必要があります（backtest.run の docstring を参照）。

---

## 貢献 / 拡張案

- execution 層に実際の注文送信ロジック（kabuステーション API）を追加する
- AI スコア生成モジュール（ai scoring）を統合し ai_scores を自動生成する
- 分足シミュレーション / 高頻度対応のため clock / simulator を拡張する
- ETL の品質チェックを強化しアラート・レポート出力を追加する

---

この README はコードベースから抽出した主要機能・使用方法の要約です。より詳細な仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）が存在する想定で設計説明や注釈がソース内に多数記載されています。必要であれば特定モジュールの詳細ドキュメント（例: jquants_client のリトライ挙動、news_collector の RSS パース仕様、バックテストのポジションサイジング等）を追記します。