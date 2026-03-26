# KabuSys

日本株向けの自動売買 / 研究フレームワーク。  
データ取得（J-Quants）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などを含むモジュール群を提供します。

## 概要
KabuSys は DuckDB をデータストアに用いる日本株アルゴリズムトレーディング基盤です。  
研究用途（ファクター探索、IC 計測）から運用用途（シグナル生成 → 発注、バックテスト）まで一貫して扱えるよう設計されています。  
設計方針のポイント:
- Look-ahead bias を防ぐ取り回し（取得時刻/fetched_at の記録や「ターゲット日」ベースの計算）
- 冪等性（DB への INSERT は ON CONFLICT/RETURNING を多用）
- ネットワーク安全（RSS の SSRF 対策等）や API レート制御の実装
- バックテスト用の純粋なメモリシミュレータ実装（実行時の DB 変更を最小化）

## 主な機能一覧
- データ取得／保存
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - RSS ニュース収集（前処理・記事保存・銘柄抽出）
  - DuckDB へ冪等に保存するユーティリティ
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - ファクター探索（IC 計算・将来リターン計算・統計サマリ）
  - Z スコア正規化ユーティリティ
- 特徴量・シグナル
  - 特徴量構築（features テーブルへの正規化済み保存）
  - シグナル生成（final_score 計算、BUY/SELL の判定、signals テーブル書き込み）
- ポートフォリオ構築
  - 候補選定・重み付け（等配分 / スコア加重）
  - リスク制御（セクター上限、レジーム乗数）
  - ポジションサイジング（risk-based / equal / score）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定ロジック）
  - バックテストエンジン（データコピー・日次ループ・シグナル→約定）
  - 評価指標計算（CAGR、Sharpe、最大ドローダウン、勝率 等）
  - CLI でのバックテスト実行
- 補助
  - 設定管理（環境変数 / .env の自動ロード）
  - ニュース記事から銘柄コード抽出

## 要求環境 / 依存
- Python 3.10 以上（| 型・型エイリアスを使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging 等）

実際のパッケージでは requirements.txt / pyproject.toml に依存を記載してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Mac/Linux)
   - .venv\Scripts\activate     (Windows)
3. 依存をインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
4. パッケージを開発モードでインストール（任意）
   - pip install -e .
5. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（config.py が .git または pyproject.toml を基準に検索）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
6. DuckDB スキーマ初期化
   - 本リポジトリには schema 初期化スクリプトが想定されています（kabusys.data.schema.init_schema を利用）。
   - DuckDB ファイルを作成し、必要なテーブル（prices_daily, raw_prices, raw_financials, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols 等）を準備してください。

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：データ取得）
- KABU_API_PASSWORD: kabuステーション API パスワード（運用時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

注意: Settings オブジェクトは未設定の必須変数に対して ValueError を送出します。

## 使い方（例）

1) バックテスト（CLI）
- DuckDB に必要テーブルが揃っていることを前提に、バックテストを実行できます。

例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-29 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based

主なオプション:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --db : DuckDB ファイルパス（必須）
- --cash : 初期資金（JPY）
- --allocation-method : equal | score | risk_based
- --slippage / --commission / --max-position-pct / --max-utilization / --max-positions / --lot-size など多数

2) 特徴量構築をプログラムから呼ぶ
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("path/to/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features updated: {n}")
conn.close()
```

3) シグナル生成を呼ぶ
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("path/to/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,5))
print(f"signals generated: {count}")
conn.close()
```

4) J-Quants からデータ取得 + 保存
```python
import duckdb
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

conn = duckdb.connect("path/to/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print(f"saved rows: {saved}")
conn.close()
```

5) ニュース収集ジョブ（RSS）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("path/to/kabusys.duckdb")
# known_codes を渡すと記事→銘柄紐付けが行われる
known_codes = {"7203","6758","9432"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

## ディレクトリ構成（主なファイル）
（このプロジェクトで与えられたコードに基づく要約）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env 管理と Settings
  - data/
    - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         — RSS 収集・記事保存・銘柄抽出
    - (schema.py 等が別ファイルとして想定される)
  - research/
    - factor_research.py        — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py    — 将来リターン、IC、統計サマリ
  - strategy/
    - feature_engineering.py    — features テーブル作成（正規化・UPSERT）
    - signal_generator.py       — final_score 計算・BUY/SELL 生成・signals 書込
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数計算・aggregate cap
    - risk_adjustment.py        — セクター上限・レジーム乗数
  - backtest/
    - engine.py                 — バックテストの全体ループ（run_backtest）
    - simulator.py              — ポートフォリオシミュレータ・約定ロジック
    - metrics.py                — バックテスト評価指標
    - run.py                    — CLI エントリポイント
    - clock.py                  — 模擬時計（将来用途）
  - portfolio/                  — 上記のポートフォリオ関連
  - execution/                  — 発注層（空ファイル/拡張ポイント）
  - monitoring/                 — 監視・アラート層（拡張ポイント）
  - research/                   — 研究用モジュール群

（上記は抜粋です。実際のリポジトリでは data.schema や DB 初期化スクリプト、ドキュメント等が別に含まれる想定です。）

## 開発上の注意点 / 補足
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュが組み込まれていますが、API 利用時は利用規約・レート上限を遵守してください。
- バックテスト関数 run_backtest は本番 DB を直接更新しないために、必要データをインメモリ DuckDB にコピーして実行します。ただし一部テーブル（positions 等）をバックテスト内部で読み書きするため、十分なデータ（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が事前準備されている必要があります。
- 単位関連（円、株数）や lot_size（単元）は日本株仕様を前提にしているため、他市場に流用する場合は注意が必要です。

---

さらなるセットアップ手順（schema の初期化やサンプルデータの用意）、運用手順、CI 用テスト例などは別途ドキュメント化することを推奨します。必要であれば README の英語版や詳細導入手順、schema の雛形作成手順も作成します。どの情報がさらに欲しいか教えてください。