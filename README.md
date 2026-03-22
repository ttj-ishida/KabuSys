# KabuSys

日本株自動売買システム（研究・データ基盤・戦略・バックテスト含む）  
このリポジトリは、J‑Quants からのデータ取得、特徴量作成、シグナル生成、バックテスト、ニュース収集などを含む一連のコンポーネントを備えた日本株向けのトレーディング基盤（ミニマム実装）です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーで構成されています。

- Data Layer: J‑Quants API クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン、データ品質チェック
- Research Layer: ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索（IC、将来リターン）
- Strategy Layer: ファクター正規化、最終スコア計算、BUY/SELL シグナル生成
- Backtest Layer: ポートフォリオシミュレータ、バックテストエンジンと評価指標
- Execution / Monitoring: 発注・監視層の雛形（今後の実装を想定）

設計上のポイント:
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- DuckDB を主な永続ストレージとして使用（:memory: でインメモリテスト可）
- 冪等性（ON CONFLICT / upsert）、トランザクションで安全な書き込み
- API レート制御・リトライ・トークン自動更新等の堅牢なクライアント実装

---

## 主な機能一覧

- J‑Quants クライアント
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制限、リトライ、トークン自動更新
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）

- ETL / Data Pipeline
  - 差分取得（最終取得日からの差分）
  - 保存・バックフィル機能、品質チェックのフック

- News Collector
  - RSS フィード取得・テキスト前処理・記事ID生成（URL 正規化 + SHA256）
  - SSRF 対策、応答サイズ制限、XML サニタイズ
  - raw_news / news_symbols への保存

- Research / Feature Engineering
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - クロスセクション Z スコア正規化（データ.stats.zscore_normalize）
  - features テーブルへの UPSERT（冪等）

- Strategy / Signal Generation
  - 正規化済みファクター + AI スコアを統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL 条件（ストップロス等）
  - signals テーブルへの日付単位置換

- Backtest フレームワーク
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループでの約定・時価評価・シグナル生成の統合
  - バックテストメトリクス（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

---

## 動作要件（概略）

- Python 3.10 以上（typing の新しい構文を使用）
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J‑Quants API / RSS フィード）
- 必要な環境変数（下記参照）

プロジェクト向けの最低限の pip コマンド例:
```
pip install duckdb defusedxml
```
（必要に応じて requirements.txt を用意して pip install -r する想定）

---

## 環境変数（必須 / 推奨）

Settings クラスは環境変数から設定を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（CWD に依存しない）。

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注実装を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 開発環境フラグ: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動的な .env ロードを無効化（テスト用）

.env ファイルのパースはシェル風の書式をサポートします（export プレフィックス・クォート・コメント等）。

---

## セットアップ手順（簡易）

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements.txt を用意していれば `pip install -r requirements.txt`）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定してください（例は下記）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: でも可
   conn.close()
   ```

---

## 使い方（例）

1) バックテスト（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
出力にバックテストメトリクス（CAGR, Sharpe など）が表示されます。

2) データ取得（ETL）の基本フロー（例: 株価差分取得）
```py
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
# target_date は通常当日
fetched, saved = run_prices_etl(conn, target_date=date.today())
conn.close()
```
（run_prices_etl は内部で get_last_price_date を参照し差分取得を行います。id_token を明示的に渡すことも可能です。）

3) 特徴量構築（features テーブル更新）
```py
import duckdb
from datetime import date
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"features updated: {n}")
```

4) シグナル生成
```py
import duckdb
from datetime import date
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ
```py
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
conn.close()
print(results)
```

---

## 開発時のヒント

- Settings はモジュール読み込み時に .env / .env.local を自動でロードします。テスト中に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマ初期化は冪等です。既存テーブルがあればスキップされます。
- J‑Quants API のトークン周りは自動更新を試みます。403/401 などが発生したら環境変数のトークンを確認してください。
- NewsCollector は XML パースに defusedxml を使用し、SSRF や Gzip Bomb 対策が組み込まれています。
- バックテストは本番 DB を直接汚さないため BT 用に in-memory DuckDB に必要テーブルをコピーして実行します。

---

## ディレクトリ構成

以下は主要ファイルの概観（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J‑Quants API クライアント + 保存関数
    - news_collector.py              — RSS 収集 / 前処理 / DB 保存
    - pipeline.py                    — ETL パイプライン（差分取得等）
    - schema.py                      — DuckDB スキーマ初期化
    - stats.py                       — 統計ユーティリティ（zscore 等）
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py         — 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル作成
    - signal_generator.py            — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py                      — バックテストエンジンと補助関数
    - simulator.py                   — ポートフォリオシミュレータ
    - metrics.py                     — バックテスト指標計算
    - run.py                         — CLI エントリポイント
    - clock.py                       — 将来用の模擬時計
  - execution/
    - __init__.py                    — 発注レイヤの雛形（実装は拡張想定）
  - monitoring/                       — 監視・メトリクス（将来拡張用）

（実際のリポジトリは src/kabusys 以下に実装ファイルが置かれています）

---

## 参考 / 注意点

- 本プロジェクトは学習・研究・プロトタイプ向けのサンプル実装です。ライブ運用を行う場合は十分な検証、監査、法令順守（金融商品取引法等）を行ってください。
- 発注・ライブ実行機能はセキュリティや外部依存（kabuステーションなど）が関係するため、本実装のまま本番接続するのは推奨しません。必ずステージング環境での検証を行ってください。
- 資料（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）は実装の設計意図を理解する上での補助資料です（リポジトリに添付していれば参照してください）。

---

もし README に追記したい具体的な使い方（ETL の細かい引数例、CI／テスト、Docker 化、requirements.txt の整備など）があれば教えてください。必要に応じてサンプル .env.example や使い方のコードスニペットを追加します。