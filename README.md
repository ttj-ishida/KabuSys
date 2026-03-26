# KabuSys

日本株向けの自動売買 / 研究フレームワーク。  
DuckDB を中心にしたデータパイプライン、因子計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集までを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（各処理は target_date 時点のデータのみを使用）
- DuckDB をデータストアに採用し、SQL と Python を組み合わせて処理
- バックテストはメモリ内シミュレータで再現可能
- 外部 API 呼び出しはデータ収集層に限定（実行層とは分離）

バージョン: 0.1.0

---

## 機能一覧

- data
  - J-Quants API クライアント（fetch / save 関数、リトライ・レートリミット・トークン更新対応）
  - ニュース収集（RSS -> raw_news、SSRF 対策、記事正規化、銘柄抽出）
  - DB スキーマ初期化・カレンダー管理 等（data.schema / calendar_management）
- research
  - ファクター計算：momentum / volatility / value（prices_daily / raw_financials 参照）
  - 研究用ユーティリティ：Z スコア正規化、IC 計算、要約統計
- strategy
  - 特徴量エンジニアリング（features テーブル生成、Z スコアクリップ）
  - シグナル生成（features + ai_scores -> BUY / SELL signals、Bear レジーム抑制、SELL 優先）
- portfolio
  - 候補選択、配分重み計算（等配分 / スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - サイジング（risk-based / equal / score、単元丸め、aggregate cap）
- backtest
  - ポートフォリオシミュレータ（スリッページ・手数料・部分約定・日次評価）
  - バックテストエンジン（データのコピー、ループ、シグナル生成、発注処理）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio 等）
  - CLI からの実行スクリプト（python -m kabusys.backtest.run）
- monitoring / execution
  - 実運用・発注層・監視はモジュール名で用意（コードベースでは一部実装が未配置の場合あり）

---

## 前提 / 必要環境

- Python 3.10+
  - 型注釈に `X | Y`（PEP 604）を使用しているため 3.10 以上を想定
- DuckDB（Python パッケージ：duckdb）
- defusedxml（ニュースパーシングの安全化）
- （任意）ネットワーク接続 / J-Quants API トークン / kabu API / Slack など

推奨パッケージ（最低限）:
- duckdb
- defusedxml

インストール例:
```
python -m pip install duckdb defusedxml
```

プロジェクトに requirements.txt があればそちらを利用してください。

---

## セットアップ手順

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール
   ```
   pip install duckdb defusedxml
   # 必要に応じてその他のパッケージを追加
   ```

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL — ログレベル (DEBUG/INFO/...)（デフォルト: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=yyyy...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - コード内の data.schema.init_schema を使って DB を初期化します（スキーマ定義ファイルに依存）。
   - 例（Python REPL、スクリプト等）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # 必要に応じて初期データを投入
     conn.close()
     ```

---

## 使い方（代表的なワークフロー）

1. データ収集（J-Quants）
   - 株価 / 財務 / 上場銘柄情報 / マーケットカレンダー を取得する
   - 例: fetch + save の流れ
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     from kabusys.data.jquants_client import get_id_token

     token = get_id_token()  # settings.jquants_refresh_token を使用
     records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     conn = init_schema("data/kabusys.duckdb")
     save_daily_quotes(conn, records)
     conn.close()
     ```

2. ニュース収集（RSS）
   - run_news_collection を呼ぶと RSS を取得し raw_news / news_symbols に保存します
     ```python
     from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     res = run_news_collection(conn)
     conn.close()
     ```

3. 特徴量（features）作成
   - strategy.feature_engineering.build_features を呼び、target_date の features テーブルを更新
     ```python
     from kabusys.strategy import build_features
     conn = init_schema("data/kabusys.duckdb")
     build_features(conn, target_date=date(2024, 1, 31))
     conn.close()
     ```

4. シグナル生成
   - features / ai_scores / positions を基に signals テーブルを更新
     ```python
     from kabusys.strategy import generate_signals
     conn = init_schema("data/kabusys.duckdb")
     generate_signals(conn, target_date=date(2024, 1, 31))
     conn.close()
     ```

5. バックテスト実行（CLI）
   - 用意された CLI でバックテストを実行できます（DuckDB ファイルは事前にデータを整備しておく）
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 主要オプション:
     - --slippage, --commission, --allocation-method (equal/score/risk_based), --max-positions, --lot-size など

6. バックテスト API 呼び出し（プログラムから）
   ```python
   from kabusys.backtest.engine import run_backtest
   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   # result.history, result.trades, result.metrics を参照
   conn.close()
   ```

---

## 注意点 / 実装メモ

- 環境変数の自動読み込み
  - パッケージはルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします。
  - テスト等で自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Look-ahead バイアス対策
  - 特徴量・シグナル生成・バックテストは target_date 時点の情報のみを使うように設計されています。
  - データ取得段階でも fetched_at 等により「いつデータが得られたか」を追跡します。

- J-Quants クライアント
  - レート制限（120 req/min）に合わせた内部 RateLimiter、リトライ、401 時の自動トークン更新などを実装済みです。
  - fetch 関数はページネーションに対応しています。

- ニュース収集
  - RSS の XML パースは defusedxml を利用して安全に行っています。
  - SSRF 対策（リダイレクト先の検査 / プライベート IP ブロック / レスポンスサイズ制限）を実装しています。

- 一部モジュールは実運用向けの連携（Slack/実際の発注 API 等）を想定しており、環境変数の設定や追加実装が必要です。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルと役割（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（__version__、公開 API）

- config.py
  - 環境変数の自動ロード / Settings クラス（各種環境変数プロパティ）

- data/
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - news_collector.py — RSS 取得・正規化・DB 保存（raw_news / news_symbols）
  - schema.py — DuckDB スキーマ初期化（init_schema）など（参照箇所あり）
  - calendar_management.py — 取引日取得等（参照あり）

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py — 主要関数の再エクスポート

- strategy/
  - feature_engineering.py — features テーブル作成（Z スコア正規化等）
  - signal_generator.py — final_score 計算 -> signals テーブル（BUY/SELL）
  - __init__.py

- portfolio/
  - portfolio_builder.py — 候補選択・重み計算
  - position_sizing.py — 株数決定・丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py

- backtest/
  - engine.py — バックテスト全体ループ・データコピー・発注ロジック
  - simulator.py — ポートフォリオシミュレータ（約定ロジック・mark_to_market）
  - metrics.py — バックテストメトリクス算出
  - run.py — CLI エントリポイント
  - clock.py — 将来用途の模擬時計

- execution/
  - （発注実装のための名前空間。現状はパッケージ空）

- monitoring/
  - （監視・通知ロジックのための名前空間）

---

## 開発 / 貢献

- コードスタイル: リファクタ・タイプヒント中心。ユニットテストを追加して挙動を保証してください（このリポジトリに tests は含まれていない想定）。
- モジュール間の依存は最小化し、データベース接続を明示的に受け渡す設計です（グローバル DB 接続に依存しない）。

---

## 参考コマンド例

バックテスト実行（例）:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --max-positions 10
```

DuckDB スキーマ初期化（例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 必要な初期データを投入
conn.close()
```

---

README に不足している情報（例）:
- 実際の requirements.txt（外部依存の正確なバージョン指定）
- data.schema のスキーマ定義と初期データ投入手順
- 実運用（kabu API 連携、Slack 通知）の設定と権限まわりの手順

必要であれば、これらの追加セクション（requirements.txt のサンプル、schema 初期化手順、.env.example のテンプレート、よくあるトラブルシューティング等）を追記します。どの情報を優先して補強しますか？