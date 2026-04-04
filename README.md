# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

このリポジトリは日本株向けのデータ収集（ETL）・品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログなどを提供する内部ライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API や OpenAI（gpt-4o-mini）を外部サービスとして利用する設計になっています。

主な想定用途
- 日次 ETL による株価・財務・市場カレンダーの取得と品質チェック
- RSS ニュース収集と OpenAI による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究（ファクター計算・将来リターン・IC 計算）
- 監査ログスキーマの初期化と利用（発注・約定のトレーサビリティ）

---

## 機能一覧

- 設定管理
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須環境変数存在時の例外・検証機能

- データ（data）
  - J-Quants クライアント（認証・取得・レート制御・リトライ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（市場カレンダー / 株価 / 財務）の差分取得と保存
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、防御的実装：SSRF対策・XML防御など）
  - 監査ログスキーマ（signal_events / order_requests / executions）初期化ユーティリティ

- AI（ai）
  - ニュース NLP（銘柄単位のセンチメントを OpenAI でスコア化）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンス検証・リトライを行う

- Research（research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB SQL ベース）
  - 将来リターン算出、IC（スピアマン）計算、統計サマリー、Z スコア正規化ユーティリティ

- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - ETL 実行結果を表す ETLResult Dataclass

---

## セットアップ手順

前提
- Python 3.10+（組込みの型構文（X | Y）を使用しているため）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（v1系を想定）
- defusedxml（RSS XML の安全パース）

1. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くことで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合必須。関数引数で注入も可能）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: デフォルト data/monitoring.db
   - PID_FILE_PATH, KILL_FLAG_PATH など監視用パス

   .env の書式は shell 形式に近く、コメント・クォート・export プレフィックスに対応します。

---

## 使い方（主要な関数・スクリプト例）

以下はライブラリを Python から利用する例です。各例は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

1. ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースをスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"書き込んだ銘柄数: {num_written}")
```

3. 市場レジームをスコア（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 研究用途のファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

5. 監査 DB 初期化（監査ログ専用 DB を作成してスキーマを適用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成されます
```

6. RSS フィードを取得（低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点
- OpenAI を使う機能は API キーが必須（関数の api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください）。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE）になっていますが、ETL / DB スキーマが必要なテーブルを事前に作成する運用が必要です。
- 日付の扱いはすべて date / datetime（タイムゾーンに対する方針は各モジュールの docstring を参照）です。バックテスト等でルックアヘッドバイアスを起こさないように設計されています。

---

## 主要モジュール / ディレクトリ構成

（抜粋、主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（各種パスやトークン、環境の検証）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news を元に銘柄別センチメントを算出し ai_scores テーブルへ書き込む
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロ記事の LLM センチメントを合成し market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、データ取得、保存関数）
    - pipeline.py
      - run_daily_etl 等の ETL パイプライン
    - etl.py
      - ETLResult の公開（再エクスポート）
    - news_collector.py
      - RSS 取得と前処理ユーティリティ（SSRF 対策、XML 防御等）
    - calendar_management.py
      - market_calendar の管理および営業日ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）のスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility / liquidity の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

その他（パッケージ外）
- README.md（本ファイル）
- .env.example（想定される環境変数の例を用意してください）※このリポジトリ内に存在しない場合は作成を推奨

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が必要）
- KABUSYS_ENV — environment ('development' | 'paper_trading' | 'live')
- LOG_LEVEL — ログレベル（'INFO' 等）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）

---

## 運用上の注意と設計方針（抜粋）

- ルックアヘッドバイアス防止: 多くの関数は date.today() を内部で参照せず、外部から target_date を注入する設計です。バックテストや日次処理では必ず明示的に日付を指定してください。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE を用いて冪等に実装されています。
- フェイルセーフ: OpenAI や外部 API 呼び出しで失敗した場合、多くの処理はスキップして継続する（例: macro_sentiment=0.0 やスコア取得失敗で該当銘柄をスキップ）よう設計されています。
- セキュリティ: RSS 取得は SSRF 対策・XML の安全パース・最大受信サイズ制限等を実装しています。
- ロギング: 各モジュールは logger を使用しており、LOG_LEVEL によって制御してください。

---

## 開発者向けメモ

- テスト時に .env の自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しのテストは各モジュールの _call_openai_api を unittest.mock.patch で差し替えて実施できます。
- DuckDB の executemany には空リストを渡せない場面があるため、実装側で空チェックを入れています（互換性確保）。
- jquants_client は内部で固定レート制御（_RateLimiter）とリトライロジックを実装しています。API レートに注意してください。

---

README の内容はこのコードベースの主要設計・使い方を簡潔にまとめたものです。実際の運用スクリプト・スケジューリング（cron / systemd / コンテナ化）・詳細な DB スキーマやマイグレーション手順は運用者側で整備してください。必要であれば、サンプルの docker-compose / systemd ユニットや運用手順書のテンプレートも作成できます。必要なら指示してください。