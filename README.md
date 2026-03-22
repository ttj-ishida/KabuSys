# KabuSys

日本株向けの自動売買システム用ライブラリ。データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、バックテストシミュレーション、ニュース収集などを含んだモジュール群を提供します。

主に研究（research）→特徴量生成→シグナル生成→発注（execution）→モニタリング のワークフローを想定しています。DuckDB を内部DBとして利用します。

---

## 主な機能

- データ収集
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - JPX マーケットカレンダー・株価日足・財務データの取得と DuckDB への保存
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む ETL ワークフロー
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成（URL正規化＋SHA256）、銘柄紐付け
  - SSRF / gzip / サイズ上限対策 等の安全実装
- 研究（research）
  - ファクター計算（momentum, volatility, value 等）
  - ファクター探索（将来リターン、IC、統計要約）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化（Zスコア）・ユニバースフィルタ適用・features テーブルへのUPSERT
- シグナル生成（strategy.signal_generator）
  - 正規化済みファクター + AIスコアを統合して final_score を計算、BUY/SELL シグナル生成
  - Bear レジーム抑制、エグジットルール（ストップロス等）
- バックテスト（backtest）
  - ポートフォリオシミュレータ（約定モデル: スリッページ・手数料・資金管理）
  - バックテストエンジン（本番DBからインメモリDuckDBへデータコピーして日次ループ実行）
  - 評価メトリクス（CAGR, Sharpe, Max Drawdown, 勝率等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- DB スキーマ管理
  - DuckDB 用スキーマ定義と初期化ユーティリティ（init_schema / get_connection）
- 設定管理
  - 環境変数（.env / .env.local）自動ロード機能、キーの必須チェック

---

## 動作環境（推奨）

- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- 必要パッケージの一例:
  - duckdb
  - defusedxml
  - （その他: 実行環境に応じて urllib, typing, logging は標準ライブラリで提供）

パッケージはプロジェクトに requirements.txt を置いている想定で、次のようにインストールします:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# (requirements.txt がない場合)
pip install duckdb defusedxml
```

---

## 環境変数（主な項目）

以下は必須または重要な環境変数の例です（kabusys.config.Settings から取得されます）。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネルID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定は次のように取得できます:

```python
from kabusys.config import settings
print(settings.duckdb_path)
```

未設定の必須キーを参照すると ValueError が発生します（.env.example を参考にしてください）。

---

## セットアップ手順（要点）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   requirements.txt が無い場合は最低限 duckdb と defusedxml を入れてください:

   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに .env を作成し、上記の必要なキーを設定します。
   - .env.local を使ってローカルのみ上書きすることも可能です（.env.local は .env を上書きします）。

4. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   または Python REPL / スクリプトで実行して必要なテーブルを作成します。

---

## 使い方（主要なワークフロー例）

以下は代表的な呼び出し例です。

- データ取得（J-Quants） & 保存（ETL）

  jquants_client の fetch_* / save_* 関数と data.pipeline の ETL ヘルパを使用します。例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  # target_date には取得終了日（通常は当日）を指定
  res = run_prices_etl(conn, target_date=date.today())
  print(res.to_dict())  # ETLResult のサマリ
  conn.close()
  ```

- ニュース収集（RSS）と保存

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効コード集合（任意）
  results = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
  print(results)
  conn.close()
  ```

- 特徴量計算（features テーブル生成）

  features を作るには DuckDB 接続と基準日を渡します:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {n}")
  conn.close()
  ```

- シグナル生成

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,1,31))
  print(f"signals generated: {count}")
  conn.close()
  ```

- バックテスト（CLI）

  プロジェクトにはバックテスト用の CLI エントリポイントがあります:

  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

  このコマンドは指定期間のバックテストを実行し、結果（CAGR, Sharpe 等）を出力します。内部で本番DBの必要なテーブルをインメモリにコピーしてシミュレーションを行います。

---

## よくあるトラブルと対処

- 環境変数が足りない / ValueError が出る:
  - settings で必須項目が参照されると未設定時に例外になります。.env を作成して必要なキーを追加してください。

- .env の自動読み込みを無効化したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB の権限/ディレクトリがない:
  - init_schema は親ディレクトリを自動作成しますが、書き込み権限を確認してください。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS ニュース収集・保存処理
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — Z スコア等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（差分更新等）
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value 等のファクター計算
    - feature_exploration.py  — 将来リターン計算・IC・統計要約
  - strategy/
    - __init__.py
    - feature_engineering.py  — 特徴量の正規化・features への保存
    - signal_generator.py     — final_score 計算と BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py               — バックテストエンジン（全体ループ）
    - simulator.py            — 約定・ポートフォリオシミュレータ
    - metrics.py              — バックテスト評価指標計算
    - run.py                  — CLI エントリポイント
    - clock.py                — 模擬時計（将来拡張用）
  - execution/
    - __init__.py             — 発注層（将来の実装）
  - monitoring/                — モニタリング関連（未実装 / 将来追加想定）

ドキュメントや設計仕様（StrategyModel.md 等）はリポジトリ内に別途配置されている想定です（この README では主要モジュールと使い方の概要を示しています）。

---

## 貢献・拡張ポイント

- 実運用接続（kabuステーションや発注API）の実装（execution 層）
- AIスコア生成パイプラインの実装（ai_scores テーブルへの投入）
- モニタリング／アラート（Slack 連携など）
- 単体テスト・CI の整備
- 分足シミュレーション対応（SimulatedClock の活用）

---

以上。README に不足があれば、特に記載して欲しいコマンドや、補足したい設計文書（StrategyModel.md 等）の要点を教えてください。必要に応じて README を拡張します。