# KabuSys

日本株向けのデータプラットフォーム＋自動売買リサーチ基盤の Python モジュール群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）等の機能を含みます。

注意: これはライブラリ／内部モジュールの集合であり、単一の実行バイナリではありません。用途に応じてスクリプトやジョブラッパーを用意して実行してください。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX 市場カレンダー取得（ページネーション・レート制御・リトライ対応）
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損検出、重複検出、スパイク検出、日付整合性チェック（quality モジュール）
  - 品質チェックを ETL の最後に実行可能

- ニュース収集・NLP
  - RSS 取得・前処理（SSRF 対策、URL 正規化、gzip 制限など）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクター計算（research モジュール）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの DDL と初期化関数（data.audit.init_audit_schema / init_audit_db）
  - 発注→約定の UUID ベーストレーサビリティ

- 設定管理
  - .env / .env.local / OS 環境変数の読み込み（kabusys.config）
  - 必須環境変数の明示的チェック（Settings クラス）

---

## 必要条件

- Python 3.10 以上（typing の | 記法、from __future__ annotations を想定）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

プロジェクトに requirements.txt は含まれていません。利用環境に応じて上記パッケージをインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他必要なパッケージを追加でインストール
```

---

## 環境変数（主なもの）

.env/.env.local または OS 環境変数として設定します。自動読み込みの優先順位は OS 環境 > .env.local > .env です。プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

必須（ライブラリの一部機能で必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD      : kabuステーション API 用パスワード（config で必須扱い）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（利用する場合）
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID（利用する場合）

OpenAI 関連:
- OPENAI_API_KEY         : OpenAI API 呼び出し（score_news / score_regime）。関数呼び出し時に api_key を直接渡すことも可能。

任意（デフォルトあり）:
- KABUSYS_ENV            : 実行環境 ("development" / "paper_trading" / "live")。デフォルト: development
- LOG_LEVEL              : ログレベル ("DEBUG","INFO",...)。デフォルト: INFO
- DUCKDB_PATH            : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH            : SQLite 監視 DB（必要な場合）。デフォルト: data/monitoring.db

テスト等で自動 .env ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン・チェックアウト
2. 仮想環境作成と依存パッケージのインストール
   - 先に示した pip コマンド等で duckdb, openai, defusedxml をインストール
3. 環境変数設定
   - プロジェクトルートに `.env` を作成して上記の必須変数を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzz
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```
   - 機密情報は `.env.local` に置いて .gitignore で管理することを推奨

4. DuckDB 初期スキーマの用意（必要に応じて）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用 DB（raw_prices / raw_financials / market_calendar 等のテーブル）は、別途スキーマ初期化スクリプトがある前提で準備してください（本コード片は保存/更新ロジックを提供しますが、全テーブルDDL はプロジェクト別に管理されます）。

---

## 使い方（簡単な例）

以下はいくつかの主要 API の利用例です。実際はアプリケーションのジョブスケジューラ（cron, Airflow 等）から呼び出します。

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- 監査ログDB初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 監査テーブルを作成して接続を返す
```

注意点:
- score_news / score_regime は OpenAI の呼び出しを行うため OPENAI_API_KEY の設定（または api_key 引数）を忘れずに。
- ETL / 保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime 等）が前提です。必要な DDL を準備してください。

---

## 主要モジュールとディレクトリ構成

以下は src/kabusys 配下の主なファイルと役割（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の読み込みと Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースセンチメントの取得（OpenAI 呼び出し、バッチ、検証、DuckDB へ保存）
    - regime_detector.py  : ETF MA とマクロニュースを合成した市場レジーム判定（OpenAI 使用）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（認証、取得、DuckDB への保存）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - etl.py              : ETLResult の再エクスポート
    - news_collector.py   : RSS 収集・前処理・保存補助
    - calendar_management.py : 市場カレンダー管理、営業日判定ユーティリティ
    - stats.py            : zscore_normalize 等の統計ユーティリティ
    - quality.py          : データ品質チェック（欠損、重複、スパイク、日付不整合）
    - audit.py            : 監査ログテーブル DDL / 初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py  : Momentum / Volatility / Value ファクター計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク変換

（上記はプロジェクト内の主要コンポーネントの説明です。実際のアプリケーションでは、テーブル定義やジョブラッパーを追加してください。）

---

## 運用上の注意点

- Look-ahead バイアス回避
  - 多くのモジュールは date パラメータを明示的に受け取り、datetime.today()/date.today() を直接参照しない設計になっています。バックテスト時は過去データだけが利用されるよう注意してください。

- 冪等性
  - J-Quants からの取得 → DuckDB 保存は ON CONFLICT DO UPDATE を利用して冪等性を担保しています。

- API レート制御 / リトライ
  - J-Quants クライアントは固定間隔スロットリングと指数バックオフを実装しています。OpenAI 呼び出しもリトライロジックを内包しています。

- セキュリティ
  - news_collector は SSRF 対策（リダイレクト中のホスト検査、プライベートIP拒否）や XML の defusedxml 利用、受信サイズ制限などを実装しています。

---

## 貢献・拡張

- 新しい ETL 対象やスキーマ、監査項目、研究用の指標を追加する場合は、既存のモジュールと同様に DuckDB 接続を受け取り、冪等で保存する実装方針を踏襲してください。
- OpenAI モデルやプロンプトは将来の改善が想定されます。news_nlp / regime_detector のプロンプトやバッチサイズ、トークン制限などは用途に応じて調整してください。

---

この README はコードベースの概要と基本的な利用方法をまとめたものです。実運用では環境ごとの設定、DB スキーマ準備、監視・ロギングの整備、ジョブスケジューラとの連携が必要になります。必要であればセットアップスクリプトや初期スキーマ（DDL）・サンプル .env.example を追加で作成しますので指示してください。