# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（研究・データパイプライン・戦略・バックテスト・実行レイヤーを含む）です。  
本リポジトリは以下を主に提供します。

- データ収集（J-Quants / RSS ニュース）
- DuckDB ベースのデータスキーマと ETL パイプライン
- ファクター計算・特徴量エンジニアリング
- シグナル生成ロジック
- バックテストエンジン（ポートフォリオシミュレータ・メトリクス）
- ニュース収集・銘柄紐付け機能

プロジェクト全体は「ルックアヘッドバイアス回避」「冪等性」「堅牢なエラーハンドリング」を設計方針として実装されています。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env）について
- 使い方（簡単な例）
  - スキーマ初期化
  - ETL（価格 / 財務 / カレンダー）
  - 特徴量作成とシグナル生成
  - バックテスト実行（CLI）
  - ニュース収集
- ディレクトリ構成（主要ファイルの説明）
- 開発上の注意点

---

## プロジェクト概要

KabuSys は研究 → 本番のデータ基盤と戦略実行を一貫して扱えるよう設計された Python パッケージです。  
DuckDB をデータ永続層に利用し、J-Quants API や RSS を介したデータ取得、特徴量計算、シグナル生成、発注（execution 層を別実装可能）およびバックテスト機能を備えています。

---

## 主な機能（機能一覧）

- データ収集
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー）
  - RSS ベースのニュース収集（記事の前処理、トラッキングパラメータ除去、SSRF 対策）
- データ基盤（DuckDB）
  - 完全なスキーマ定義（raw / processed / feature / execution 層）
  - 冪等な保存ロジック（ON CONFLICT / RETURNING を活用）
- ETL パイプライン
  - 差分取得（バックフィルを含む）、品質チェックフック（quality モジュールを参照）
- 研究用モジュール
  - ファクター計算: momentum / volatility / value
  - 特徴量探索: forward returns / IC / summary
  - クロスセクション Z スコア正規化
- 戦略（Strategy）
  - 特徴量合成と Z スコアクリップ（build_features）
  - シグナル生成（generate_signals）：複合スコア、Bear レジーム抑制、BUY/SELL の作成
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、全量クローズの SELL）
  - 日次ループでの時価評価・発注シミュレーション
  - メトリクス算出（CAGR / Sharpe / MaxDD / WinRate / PayoffRatio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- セキュリティ・堅牢性
  - RSS の XML パースに defusedxml を使用
  - SSRF 防止・プライベートIP ブロック
  - API レート制御、再試行・トークン自動リフレッシュ

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法 (X | Y) を利用しているため）
- pip、venv 等の環境管理ツール
- 主な依存パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで実装している箇所が多いため、追加の HTTP ライブラリは不要（urllib を使用）

依存はプロジェクト配布時に requirements.txt / pyproject.toml にまとめてください（このコードベースでは明示的なファイルは含まれていません）。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

2. 必須パッケージのインストール
   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用）

3. リポジトリをインストール（開発モード）
   ```bash
   pip install -e .
   ```

4. DuckDB スキーマ初期化（デフォルトファイルパスを使う例）
   Python REPL / スクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

---

## 環境変数（.env）について

kabusys は起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動ロードします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API（発注等）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO

Settings は `kabusys.config.settings` からプロパティとして取得できます。必須設定が欠けている場合は ValueError が送出されます。

---

## 使い方（主要な操作例）

以降はサンプルコードと CLI 利用法の例です。DuckDB への接続は `kabusys.data.schema.init_schema` を使って確保してください。

1) スキーマ初期化（既にやっている想定）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) ETL（株価差分取得の実行例）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

# target_date を指定して差分 ETL を実行 (戻り値: (fetched_count, saved_count) など)
fetched, saved = run_prices_etl(conn, target_date=date.today())
```
（pipeline モジュールは差分、バックフィル、品質チェックをサポートします。詳細は pipeline の docstring を参照）

3) 特徴量作成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

# generate_signals は signals テーブルに BUY/SELL を書き込む（冪等）
total = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {total}")
```

5) バックテスト（CLI）
リポジトリにはバックテスト用の CLI エントリポイントがあります。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb
```
利用可能な引数:
- --start / --end : 開始/終了日（YYYY-MM-DD）
- --cash : 初期資金（デフォルト 10000000）
- --slippage : スリッページ率（デフォルト 0.001）
- --commission : 手数料率（デフォルト 0.00055）
- --max-position-pct : 1銘柄最大比率（デフォルト 0.20）
- --db : DuckDB ファイルパス（必須）

6) ニュース収集（RSS）フルジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を与えると記事→銘柄紐付けを行います
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージルート
  - config.py — 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制御・リトライ・保存関数を含む）
    - news_collector.py — RSS 取得・前処理・DB 保存、銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema()
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - pipeline.py — ETL パイプライン（差分取得 / backfill / 品質チェック）
  - research/
    - factor_research.py — momentum / volatility / value のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — ファクター合成・ユニバースフィルタ・Z スコア処理
    - signal_generator.py — final_score 計算と BUY/SELL 生成
  - backtest/
    - engine.py — バックテストの全体ループ、in-memory コピー、I/O helper
    - simulator.py — PortfolioSimulator（擬似約定、マークトゥマーケット）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI ラッパー（python -m kabusys.backtest.run）
    - clock.py — 将来拡張用の模擬時計
  - execution/ — 発注・実行層（今後の実装 / 外部接続用）
  - monitoring/ — 監視・アラート（今後の実装）

---

## 開発上の注意点 / 実装上のポリシー

- ルックアヘッドバイアス防止: 全ての戦略/研究関数は target_date 時点のデータのみ参照する設計になっています（過去データの先読みをしない）。
- 冪等性: DB への挿入は可能な限り ON CONFLICT / DO UPDATE / DO NOTHING を使用して再実行可能にしています。
- セキュリティ:
  - RSS の XML は defusedxml でパース
  - URL のリダイレクト先はプライベート IP を拒否（SSRF 対策）
- テスト性:
  - API トークン取得・HTTP 呼び出しは id_token の注入などでモック可能
  - news_collector._urlopen などをモックしてネットワーク依存を除くことができます
- Python バージョンは 3.10 以上が必須です（型表記に | を使用）。

---

もし README に追加したい内容（例えば CI / lint / testing のセットアップ、具体的な SQL スキーマの抜粋、より詳しい API 使用例、.env.example のサンプルなど）があれば教えてください。必要に応じて追記・カスタマイズします。