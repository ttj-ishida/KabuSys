# KabuSys

日本株向け自動売買／データ基盤ライブラリ (開発版)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL、ニュースベースの NLP スコアリング、リサーチ用ファクター計算、監査ログ（トレーサビリティ）および市場レジーム判定・実行支援を含むモジュール群を提供する Python パッケージです。  
主に以下を目的とします。

- J-Quants API からの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI による銘柄ごとの NLP センチメント評価
- ファクター計算・特徴量探索（リサーチ用途）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 監査ログスキーマ（シグナル→発注→約定のトレース）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計では「ルックアヘッドバイアス回避」「冪等性（INSERT ... ON CONFLICT）」や「外部 API 呼び出しのリトライ/バックオフ」「安全対策（SSRF防止等）」に配慮しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からの取得（株価日足、財務、上場情報、JPX カレンダー）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
  - レートリミット管理・トークン自動リフレッシュ・ページネーション対応

- data.pipeline
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
  - 差分取得、バックフィル、品質チェックの一括実行（ETLResult）

- data.news_collector
  - RSS 収集、URL 正規化、記事 ID 生成、raw_news へ冪等保存
  - SSRF 対策、受信サイズ制限、XML パース対策（defusedxml）

- ai.news_nlp
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコア生成
  - バッチ処理、レスポンスバリデーション、リトライ/バックオフ

- ai.regime_detector
  - ETF（1321）の 200 日移動平均乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定
  - LLM 呼び出し失敗時はフェイルセーフ（0.0）で継続

- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターンの計算、IC（スピアマン相関）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats）

- data.quality
  - 欠損・スパイク・重複・日付不整合の品質チェック（QualityIssue を返す）

- data.audit
  - 監査ログスキーマ（signal_events, order_requests, executions）の初期化と専用 DB 作成

- 設定管理（kabusys.config）
  - .env 自動読み込み（優先順位: OS 環境 > .env.local > .env）
  - 環境変数取得ラッパー（必須変数チェック、デフォルト値）

---

## 必要条件 / 依存

- Python 3.10 以上（PEP 604 の型記法や union 型記述を使用）
- 主な依存ライブラリ（コードで使用）
  - duckdb
  - openai
  - defusedxml

インストール時はプロジェクトの pyproject.toml / requirements.txt に従ってください。ここでは例示のみ：

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化されている場合）
# pip install -e .
```

---

## 環境変数（主なもの）

設定は .env(.local) または OS 環境変数で行います。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須または重要な環境変数:

- JQUANTS_REFRESH_TOKEN
  - J-Quants 用リフレッシュトークン（必須、ETL 実行時）
- KABU_API_PASSWORD
  - kabuステーション（発注）用パスワード
- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector）
- KABUSYS_ENV
  - 実行環境: one of `development`, `paper_trading`, `live`（デフォルト: development）
- LOG_LEVEL
  - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト INFO）

（オプション）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用データベース）
- PID_FILE_PATH, KILL_FLAG_PATH, 監視閾値 (CPU/MEM/DISK)

設定値は kabusys.config.settings 経由で取得できます。

---

## セットアップ手順（例）

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作成して有効化

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
```

3. 依存をインストール

```bash
pip install duckdb openai defusedxml
# またはプロジェクトに requirements があればそれを使用
# pip install -r requirements.txt
```

4. .env を作成（例）

プロジェクトルートに `.env` または `.env.local` を作成し、必要な環境変数を設定します。例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

5. データベース用ディレクトリを作成（必要なら）

```bash
mkdir -p data
```

---

## 使い方（主要な操作例）

以下は Python REPL やスクリプトからの利用例です。事前に依存と .env の準備を行ってください。

- 基本設定参照

```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path オブジェクト
print(settings.env)           # development / paper_trading / live
```

- DuckDB 接続を作って日次 ETL を実行（pipeline.run_daily_etl）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP スコアを生成（ai.news_nlp.score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written}")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（data.audit.init_audit_db）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.duckdb")
# これで signal_events/order_requests/executions テーブルが作られます
```

- 研究用ファクター計算（research）

```python
from kabusys.research import calc_momentum, calc_value
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

注意: 各関数はデータベースに想定したテーブル（raw_prices / raw_financials / raw_news / news_symbols / ai_scores / market_regime など）が存在することを前提に動作します。初期 ETL をまず実行してデータを入れてください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュールと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、公開サブモジュールの列挙

- src/kabusys/config.py
  - 環境変数の自動読み込み、設定ラッパー（settings）

- src/kabusys/ai/
  - news_nlp.py
    - ニュース記事を銘柄別に集約し OpenAI でセンチメントを算出、ai_scores へ書き込む
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を更新
  - __init__.py

- src/kabusys/data/
  - jquants_client.py
    - J-Quants API クライアント + DuckDB への保存関数
  - pipeline.py
    - ETL パイプライン（run_daily_etl など）と ETLResult
  - etl.py
    - ETLResult の公開エイリアス
  - news_collector.py
    - RSS 収集と raw_news 保存
  - calendar_management.py
    - JPX カレンダー管理、営業日判定・next/prev/get_trading_days 等
  - quality.py
    - データ品質チェック群
  - audit.py
    - 監査ログスキーマの初期化 / init_audit_db
  - stats.py
    - z-score 正規化などの汎用統計ユーティリティ
  - __init__.py

- src/kabusys/research/
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー系ファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク化ユーティリティ
  - __init__.py

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス回避のため、ライブラリは内部で date.today() を直接参照しない方針の箇所があります（多くは target_date 引数を必須／推奨）。バックテスト等で使用する際は target_date を明示してください。
- OpenAI / J-Quants API 呼び出しは課金やレート制限の対象です。実行前にキーと利用料を確認してください。
- ETL・API 呼び出しはリトライやフェイルセーフ機構を備えていますが、長時間の自動実行環境では監視（ログ・プロセス監視）を組み合わせてください。
- .env 自動読み込みはプロジェクトルート検出を行いますが、テスト時などで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に追記したい利用手順（例: systemd サービス定義、Airflow / Cron の実行例、CI 設定など）があれば教えてください。必要に応じて README を拡張します。