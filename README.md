# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集、J‑Quants API クライアントなど、戦略開発と運用に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを備えたモジュール群を提供します。

- Data：J‑Quants からのデータ取得、保存、スキーマ定義、ニュース収集、品質チェック
- Research：ファクター計算、特徴量探索（IC、将来リターン等）
- Strategy：特徴量を正規化して戦略シグナル（BUY/SELL）を生成
- Backtest：ポートフォリオシミュレータ、約定モデル、バックテストエンジンとメトリクス
- Execution / Monitoring（骨組み）：実際の発注や監視のための領域（現状は基礎コード）

設計上のポイント：
- DuckDB をデータベースとして採用し、ETL と分析を行います。
- ルックアヘッドバイアスを避ける設計（target_date 時点で入手可能なデータのみを使用）。
- 冪等性を重視した DB 操作（ON CONFLICT 等）。
- ネットワーク関連はレートリミッタ／リトライ／SSRF 対策を実装。

---

## 主な機能一覧

- J‑Quants API クライアント
  - 日足（OHLCV）・財務データ・取引カレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ

- ETL パイプライン
  - 差分取得（最終取得日からの差分取得とバックフィル）
  - 市場カレンダーの先読み、品質チェックフレームワーク

- ニュース収集
  - RSS フィード取得、前処理、SSRF/サイズ/圧縮対策、記事ID生成、銘柄抽出・紐付け

- ファクター計算 / 特徴量エンジニアリング
  - Momentum / Volatility / Value 等のファクター計算
  - Z スコア正規化・ユニバースフィルタ・features テーブルへの保存

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL の判定と signals テーブルへの保存

- バックテスト
  - PortfolioSimulator（スリッページ・手数料モデル実装）
  - 日次ループでの約定・評価・シグナル適用
  - メトリクス（CAGR、Sharpe、MaxDrawdown、勝率、Payoff 等）
  - CLI 実行用モジュール（python -m kabusys.backtest.run）

---

## セットアップ手順

前提
- Python 3.10 以上（type hint の | を利用しているため）
- DuckDB をインストール可能な環境

推奨手順（ローカル開発）

1. リポジトリをクローン / パッケージを配置
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール（最小）
   ```
   pip install duckdb defusedxml
   ```
   補足：実運用では requests 等の追加依存やロギング、Slack 連携用ライブラリ等を導入する可能性があります。

4. (任意) パッケージを開発モードでインストール
   ```
   pip install -e .
   ```

5. データベーススキーマ初期化
   Python REPL やスクリプトから:
   ```py
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   またはインメモリ:
   ```py
   init_schema(":memory:")
   ```

環境変数
- 自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml から探索）から読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（Settings 参照）:
  - JQUANTS_REFRESH_TOKEN : J‑Quants の refresh token
  - KABU_API_PASSWORD     : kabu API 用パスワード
  - SLACK_BOT_TOKEN       : Slack 通知用 bot token
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
- 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH, SQLITE_PATH
- .env の書式は標準的な KEY=VALUE で、export KEY=...、クォート、コメント処理に対応しています。

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な利用例）

1) DuckDB スキーマ初期化
```sh
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

2) J‑Quants から日足を取得して保存（例）
```py
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

# トークンは settings で取得されるため、環境変数を設定しておく
records = jq.fetch_daily_quotes(date_from=None, date_to=None)  # 引数は必要に応じて指定
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

3) ニュース収集ジョブ（RSS）を実行して DB に保存
```py
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（任意）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

4) 特徴量構築（features のアップサート）
```py
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 01, 31))
print("features upserted:", count)
conn.close()
```

5) シグナル生成
```py
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
signals = generate_signals(conn, target_date=date(2024, 01, 31))
print("signals created:", signals)
conn.close()
```

6) バックテスト（CLI）
DuckDB ファイルが事前準備されている前提で、コマンドラインから実行できます。
```sh
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
オプション:
- --slippage (デフォルト 0.001)
- --commission (デフォルト 0.00055)
- --max-position-pct (デフォルト 0.20)

7) バックテスト API を Python から呼ぶ
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## ディレクトリ構成

（プロジェクトの src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J‑Quants API クライアント、保存ユーティリティ
    - news_collector.py               — RSS ニュース収集・前処理・保存
    - schema.py                       — DuckDB スキーマ定義・init_schema
    - stats.py                        — Zスコア等の統計ユーティリティ
    - pipeline.py                     — ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py              — Momentum/Value/Volatility 計算
    - feature_exploration.py          — IC/将来リターン/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py          — features テーブル作成
    - signal_generator.py             — final_score 計算・signals テーブル作成
  - backtest/
    - __init__.py
    - engine.py                       — バックテスト全体ループ
    - simulator.py                    — 約定モデル・ポートフォリオシミュレータ
    - metrics.py                      — バックテスト評価指標
    - run.py                          — CLI エントリポイント
    - clock.py                        — 将来拡張用の模擬時計
  - execution/                         — 発注・実行に関する領域（現状スケルトン）
  - monitoring/                        — 監視・通知等（骨組み）

---

## 追加情報 / 注意点

- Python バージョン: 3.10+
- DuckDB: データ量に応じてディスクパス（DUCKDB_PATH）を適切に設定してください。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml）を基準に探索し、OS 環境変数より低優先度で .env → .env.local を読み込みます。テスト時等には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ上限、gzip 解凍後のチェックなどの防御を組み込み済みです。
  - jquants_client はレート制限・リトライ・トークン自動更新を備えています。
- 実運用での注意:
  - 実際に発注する execution 層は慎重に実装・レビューを行なってください（本リポジトリは発注 API の呼び出しと実口座での動作を前提とする設計になっていますが、現状は発注層の詳細実装に注意が必要）。
  - Live 運用時は KABUSYS_ENV=live を設定し、ログレベルや通知などの設定を厳密に管理してください。

---

## 貢献・拡張

- 新しいファクターやニュースソースを追加する場合は、対応モジュール（research/*.py, data/news_collector.py）に機能追加をしてください。
- ETL の運用性向上や品質チェックを強化するプラグインの追加を歓迎します。
- issue / PR の際は、再現可能な最小ケースとサンプルデータ（あるいはモック）を添えてください。

---

必要に応じて README を更に具体的な CLI コマンド例、.env.example、ユニットテストの実行方法などで拡張できます。追加で書きたいセクションがあれば教えてください。