# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

このリポジトリは、日本株のデータ収集（J-Quants）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、ETL パイプライン、および監査ログ（発注→約定のトレーサビリティ）を提供するモジュール群です。バックテストや自動売買の基盤処理を想定した設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / インストール
- 環境変数（.env）と設定
- セットアップ手順
- 使い方（主要な API とスニペット）
- ディレクトリ構成（主なモジュール説明）
- 補足・設計方針

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた株価（OHLCV）・財務データ・市場カレンダーの差分取得と DuckDB 保存（ETL）
- RSS を用いたニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化ユーティリティ
- 環境変数管理と自動 .env 読み込み（プロジェクトルートから）

設計上の特徴：
- ルックアヘッドバイアス防止のため、内部で date.today() などを不用意に参照しない手法を採用
- DuckDB を用いたオンディスク／インメモリのデータ管理
- 各種 API 呼び出しに対するリトライ・フェイルセーフ設計

---

## 機能一覧

主な提供機能（モジュール別）
- kabusys.config: 環境変数の読み込み・検証（.env / .env.local 自動読み込み）
- kabusys.data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save の実装）
  - ニュース収集（RSS -> raw_news）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- kabusys.ai:
  - news_nlp.score_news: ニュースから銘柄ごとの ai_score を生成して ai_scores テーブルに保存
  - regime_detector.score_regime: ma200 とマクロニュース LLM を組み合わせて market_regime に書き込む
- kabusys.research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 監査（audit）スキーマのDDL 定義・初期化

---

## 前提条件 / インストール

推奨 Python バージョン：3.10 以上（PEP 604 の型表記などを使用）

主な依存パッケージ（抜粋）:
- duckdb
- openai
- defusedxml

pip でのインストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発インストール（setup がある場合）
# pip install -e .
```

requirements.txt や pyproject.toml があればそちらを使用してください。

---

## 環境変数（.env）と設定

kabusys.config.Settings により環境変数から設定を取得します。プロジェクトルートにある `.env` / `.env.local` が自動的に読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

重要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注と連携する場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot Token
- SLACK_CHANNEL_ID: 通知先チャンネル ID
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（例: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

例（.env）:
```env
JQUANTS_REFRESH_TOKEN=xxxxxxx
OPENAI_API_KEY=sk-xxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要なパッケージをインストール（duckdb / openai / defusedxml 等）
4. プロジェクトルートに `.env` を作成し、必要なキーを設定
5. DuckDB の初期スキーマを作成（必要に応じてスクリプトを実行）
   - 監査ログ専用 DB を初期化する例（スニペット参照）

---

## 使い方（主要 API とスニペット）

以下は代表的な利用例です。実運用用スクリプトからこれらの関数を呼ぶ想定です。

- DuckDB 接続:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（ai_scores へ書き込む）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```
score_news は OpenAI の API キー（引数 api_key または環境変数 OPENAI_API_KEY）を利用します。

- 市場レジーム判定（market_regime テーブルへ書き込み）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用 DuckDB を作る）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これでテーブルとインデックスが作成されます
```

- ファクター計算の利用例:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
# 結果は dict のリストで返却されます
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出しはネットワーク・料金が発生します。テスト時はモックを利用することを推奨します（コード内で patch しやすいように設計されています）。
- ETL / 保存処理は冪等（ON CONFLICT）です。部分的に失敗した場合でも既存データが不意に消えることを避ける工夫があります。

---

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  : .env 読み込み・Settings（環境設定）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュースから銘柄別スコアを作成し ai_scores に保存
    - regime_detector.py       : ma200 とマクロニュースを合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（fetch/save）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETLResult の公開エイリアス
    - news_collector.py        : RSS ニュース取得・前処理・保存ロジック
    - calendar_management.py   : 市場カレンダー管理（is_trading_day など）
    - quality.py               : データ品質チェック
    - stats.py                 : zscore_normalize 等の統計ユーティリティ
    - audit.py                 : 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py       : Momentum / Value / Volatility 等の計算
    - feature_exploration.py   : 将来リターン計算・IC・統計サマリー
  - ai/、data/、research/ はそれぞれのサブシステムを実装

（各モジュール内には実装の詳細、フェイルセーフ、ログ出力、トランザクション制御などの設計コメントが含まれています）

---

## 補足・設計方針（要点）

- Look-ahead バイアス防止: バックテストやファクター計算において未来データを誤って利用しないよう、時間ウィンドウや DB クエリ条件で明確に除外しています。
- 冪等性: ETL の保存は ON CONFLICT / DO UPDATE を使い、再実行しても整合性が保たれるようにしています。
- フェイルセーフ: OpenAI / J-Quants 等の外部 API 呼び出しはリトライやフォールバック（例: スコア取得失敗時は 0 を返すなど）を含み、パイプライン全体が単一障害点で停止しないように設計しています。
- テストしやすさ: OpenAI などの外部呼び出しポイントは内部関数をモック可能な形で分離しています。

---

必要であれば、README に以下の追加情報を追記できます:
- 開発用のスクリプト / make コマンド例
- CI 設定・テストの実行方法
- スキーマ定義（raw_prices / raw_financials / raw_news / ai_scores 等の CREATE TABLE 文）
- 運用時の注意（API レート・OpenAI コストなど）

ご希望があれば、上記のいずれかを追記して README を拡張します。