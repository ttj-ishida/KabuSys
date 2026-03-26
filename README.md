# KabuSys

日本株向けの自動売買 / リサーチ基盤プロジェクト。  
ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテスト・データ収集（J-Quants / RSS）を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした量的運用システムのプロトタイプです。主要コンポーネントは以下です。

- データ取得（J-Quants API、RSSニュース）と DuckDB への保存
- 研究用ファクター計算・特徴量生成（research モジュール）
- シグナル生成（strategy モジュール）
- ポートフォリオ構築・リスク調整（portfolio モジュール）
- 約定シミュレーション・バックテストエンジン（backtest モジュール）
- 実運用連携（kabuステーション / Slack 等）は設定を通じて拡張可能

設計上のポイント:
- ルックアヘッドバイアスに注意して、各ステップは target_date 時点の情報のみで動作するよう設計
- DuckDB を用いた軽量な分析 / バックテスト環境
- 冪等性（DB 書き込みは upsert / ON CONFLICT を使用）
- ネットワーク処理はレートリミッティング・リトライ等を考慮

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（認証・ページネーション・保存）
  - ニュース（RSS）収集、記事正規化、銘柄抽出、DB 保存
- research/
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの探索用ユーティリティ
- strategy/
  - 特徴量正規化・features テーブルへの保存（build_features）
  - ファクター + AI スコアを統合して売買シグナルを生成（generate_signals）
- portfolio/
  - 候補選定・重み算出（等配分・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数算出（position sizing）
- backtest/
  - ポートフォリオシミュレータ（部分約定・スリッページ・手数料を考慮）
  - バックテストエンジン（データコピー → デイリー処理 → シミュレーション）
  - メトリクス算出（CAGR、Sharpe、Max DD、勝率、Payoff 等）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- monitoring / execution などは将来の実運用連携を想定した名前空間

---

## セットアップ手順

前提:
- Python 3.10+（typing 型注釈の Union | を使用）
- pip が使用可能

1. リポジトリをクローン / 取得

2. 仮想環境作成（推奨）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```ps1
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール  
   （本コードベースでは少なくとも以下が必要になります）
   ```bash
   pip install duckdb defusedxml
   ```
   - 他に CI / 実運用で使う場合は追加パッケージや依存管理ファイルを参照してください。

4. パッケージとしてインストール（開発モード）
   ```bash
   pip install -e .
   ```
   （プロジェクトに setup / pyproject がある場合）

5. 環境変数 / .env の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（詳細は下記）。最低限設定が必須な環境変数:

   必須:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード（実運用時）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視系 SQLite のパス（デフォルト data/monitoring.db）

   自動読み込み制御:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動 .env ロードを無効化できます（テスト用途など）。

---

## 使い方

以下は代表的な実行例です。

1) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --lot-size 100
```
出力例: CAGR / Sharpe / Max Drawdown / Win Rate / Total Trades が標準出力に表示されます。

2) Python API から特徴量構築・シグナル生成を呼ぶ
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features, generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 15)

# 特徴量構築（features テーブルへ UPSERT）
build_features(conn, target)

# シグナル生成（signals テーブルへ UPSERT）
generate_signals(conn, target)
```

3) J-Quants からデータ取得して保存（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date
import duckdb

conn = init_schema("data/kabusys.duckdb")
quotes = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
save_daily_quotes(conn, quotes)
conn.close()
```

4) ニュース収集ジョブ実行（RSS ソースから raw_news 保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に stocks テーブル等から取得したコード集合
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

注意:
- データの前処理やスキーマ初期化は kabusys.data.schema.init_schema() を使って行う想定です（スキーマ/DDL は schema モジュールで管理）。
- 実運用での発注/実約定を行う場合は execution / monitoring 層と kabuステーション連携の実装が必要です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン情報
- config.py — 環境変数・設定管理（.env 自動読み込みロジック）
- data/
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
  - news_collector.py — RSS 収集、正規化、DB 保存、銘柄抽出
  - (schema.py, calendar_management 等は別ファイルでスキーマ/ユーティリティを提供)
- research/
  - factor_research.py — momentum / volatility / value のファクター計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
- strategy/
  - feature_engineering.py — 特徴量の合成・正規化・features への保存
  - signal_generator.py — final_score 計算、BUY/SELL シグナル生成（signals へ保存）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出（等配分 / スコア加重 / リスクベース）
  - risk_adjustment.py — セクター上限・レジーム乗数
- backtest/
  - engine.py — バックテストのメインループ（run_backtest）
  - simulator.py — 約定シミュレータ / ポートフォリオ状態管理
  - metrics.py — バックテスト評価指標
  - run.py — CLI ラッパー
- portfolio/, execution/, monitoring/ — 実運用向け名前空間（実装・連携を拡張）

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 注意事項 / 開発メモ

- DuckDB のスキーマ（テーブル定義）は別の schema モジュールで管理されている想定です。バックテストや ETL を実行する前にスキーマ初期化を行ってください。
- J-Quants API のレートリミット（120 req/min）と認証フロー（リフレッシュトークン → ID トークン）を考慮した実装になっています。API 利用時は token の権限・利用規約に従ってください。
- ニュース収集は SSRF や XML 脆弱性対策を施しています（ホスト検証、defusedxml、最大レスポンスサイズチェックなど）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時に自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 本リポジトリは研究/プロトタイプ用途を想定しており、実運用での注文送信前には必ずコードレビュー・追加の安全対策を行ってください（権限管理、監査ログ、フェイルセーフ等）。

---

必要であれば、README にサンプル .env.example、スキーマ初期化手順、より詳細な CLI オプション説明やユースケース（ETL パイプライン例、日次運用フロー）を追加します。どの情報を優先して追記しましょうか？