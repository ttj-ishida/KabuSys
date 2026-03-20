# KabuSys

日本株自動売買プラットフォームのライブラリ的コア実装です。  
市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査ログ・スキーマ定義など、戦略実行に必要な主要コンポーネントを含みます。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 簡単な使い方（API例）
- 環境変数（主なもの）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けの自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants API からの差分取得＋DuckDB への冪等永続化（ETL）
- 市場カレンダー管理（JPX 祝日 / SQ / 半日）
- 価格・財務データからのファクター計算（Momentum / Volatility / Value 等）
- クロスセクションの Z スコア正規化ユーティリティ
- 正規化済み特徴量を使ったシグナル生成（BUY / SELL）
- ニュース（RSS）収集とニュース→銘柄紐付け
- DuckDB スキーマ定義・初期化
- 発注・約定・監査ログ向けテーブル定義（実行層）

設計方針として、ルックアヘッドバイアスの排除、冪等処理、外部 API 呼び出しのレート制御・リトライ、DBトランザクションによる原子性を重視しています。

---

## 主な機能一覧
- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・保存関数）
  - pipeline: 日次 ETL（差分取得、backfill、品質チェック）
  - schema: DuckDB スキーマ定義と初期化（raw/processed/feature/execution 層）
  - news_collector: RSS 取得・前処理・DB保存・銘柄抽出
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value のファクター計算
  - feature_exploration: forward returns / IC / 統計サマリー
- strategy/
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- execution / monitoring: （発注層・監視のための構成が置かれる想定）
- config: .env / 環境変数の読み込み・管理

---

## 前提・依存関係
- Python 3.10 以上（モジュール内で | 型結合等を使用）
- 必須 Python パッケージ（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されているユーティリティも多いですが、実行環境には上記が必要です。

インストール例（仮想環境を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# またはプロジェクト配布用に packaging があれば pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（デフォルト）。
   - テスト時など自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. DuckDB スキーマ初期化例（Python REPL / スクリプト）:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

---

## 簡単な使い方（API例）

- DuckDB の初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL 実行（J-Quants トークンは settings から取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl, ETLResult

res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- 特徴量ビルド
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2025, 3, 20))
print(f"features built: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date(2025, 3, 20), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
```

- 市場カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants からの直接取得（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,1))
saved = save_daily_quotes(conn, records)
```

---

## 環境変数（主なもの）
KabuSys は .env ファイルおよびプロセス環境変数を参照します。プロジェクトルート（.git や pyproject.toml を基準）にある `.env`／`.env.local` を自動読み込みします。

主な必須項目:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）

その他（任意・デフォルトあり）:
- KABUSYS_ENV: environment (development / paper_trading / live) — デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...) — デフォルト "INFO"
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: モニタリング用 SQLite パス — デフォルト "data/monitoring.db"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: =1 で自動 .env ロード無効化（テスト用）

※ .env のパースはシェルライクな記法（export KEY=val、クォートや inline コメント処理等）に対応しています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      （環境変数 / 設定管理）
  - data/
    - __init__.py
    - jquants_client.py            （J-Quants API クライアント + 保存）
    - pipeline.py                  （日次 ETL / run_daily_etl 等）
    - schema.py                    （DuckDB スキーマ定義 / init_schema）
    - stats.py                     （zscore_normalize 等）
    - news_collector.py            （RSS 取得・前処理・保存・銘柄抽出）
    - calendar_management.py       （営業日判定 / calendar_update_job）
    - audit.py                     （監査ログテーブル定義）
    - features.py                  （公開インターフェース）
  - research/
    - __init__.py
    - factor_research.py           （Momentum / Volatility / Value）
    - feature_exploration.py       （forward returns / IC / summary）
  - strategy/
    - __init__.py
    - feature_engineering.py       （build_features）
    - signal_generator.py          （generate_signals）
  - execution/                      （発注層エントリ（空ファイルなど））
  - monitoring/                     （監視関連）

（上記はリポジトリの抜粋です。詳細はソース内の docstring / コメントをご参照ください。）

---

## 運用上の注意
- DuckDB への挿入は多くの箇所でトランザクション＋冪等ロジック（ON CONFLICT）を利用しています。複数プロセスから同一 DB ファイルへアクセスする場合は排他に注意してください。
- J-Quants のレート制限（120 req/min）を遵守するため内部的にスロットリングとリトライを実装しています。大量バックフィル時は API 利用制限に注意してください。
- ニュース取得は外部 RSS に依存するため SSRF 対策、受信サイズ制限、XML パース防衛（defusedxml）等の安全対策を組み込んでいます。
- 環境（KABUSYS_ENV）により振る舞い（実弾発注の有無など）を切り替える想定です。live モードでの運用は十分なテストと権限管理を行ってください。

---

## 貢献・開発
- コードはモジュールごとに docstring を充実させています。まずはローカルで DuckDB を初期化し、ETL→feature→signal の一連フローを試してください。
- テストや CI の整備、実運用での監視/アラートの追加を歓迎します。

---

README は以上です。追加してほしい使用例（cron スケジュール、Docker 化手順、CI 用のフロー等）があれば教えてください。