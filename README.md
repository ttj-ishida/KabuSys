# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）のリポジトリ用 README（日本語）

この README はコードベース（src/kabusys 以下）を基に、プロジェクト概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームを想定した Python ライブラリです。  
主に以下を提供します：

- J-Quants API からのデータ ETL（株価日足、財務、JPX カレンダーなど）
- ニュース収集と LLM を用いたニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算・研究用ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（シグナル → 発注 → 約定）スキーマの初期化支援

設計上の主眼は「ルックアヘッドバイアスを避けること」「DuckDB を用いたローカルデータ管理」「外部 API 呼び出しに対する堅牢なリトライ/フェイルセーフ」です。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS から raw_news へ、SSRF/サイズ制限/トラッキング除去対応）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events, order_requests, executions）テーブル DDL と初期化
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュース記事を銘柄ごとに OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
  - 両モジュールとも JSON モードでの LLM 呼び出し、エラー時のフェイルセーフ挙動を実装
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env 自動読み込み（プロジェクトルート：.git／pyproject.toml を基準）
  - 環境変数の管理（必須キー取得メソッドなど）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

---

## 動作環境 / 前提

- Python 3.10 以上（PEP 604 の union 型表記を使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード等）を想定

必要パッケージはプロジェクトの packaging / requirements ファイルに合わせて pip 等でインストールしてください。

例:
pip install duckdb openai defusedxml

（プロジェクトに setup/pyproject があれば pip install -e . で開発インストール可能）

---

## 環境変数（主要）

config.Settings で参照される主な環境変数：

必須
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabu API のパスワード（システム統合用）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV：development / paper_trading / live（デフォルト development）
- LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 を設定すると .env 自動読み込みを無効化
- DUCKDB_PATH（または settings.duckdb_path）：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 sqlite（デフォルト data/monitoring.db）
- OPENAI_API_KEY：OpenAI API キー（score_news や score_regime のデフォルト）

プロジェクトルートに .env/.env.local を置くと自動読み込みされます（ただし OS 環境変数が優先、.env.local は上書き）。

簡易 .env.example:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローンし、開発インストール（任意）:
   git clone <repo>
   cd <repo>
   pip install -e .

2. 必要パッケージをインストール:
   pip install duckdb openai defusedxml

   （プロジェクト側の requirements/pyproject に従ってください）

3. 環境変数を準備:
   - プロジェクトルート（.git や pyproject.toml のある場所）に .env を作成
   - 必須キー（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を設定

4. DuckDB DB ディレクトリ作成（settings.duckdb_path の親ディレクトリが自動作成される関数もありますが、手動でも可）:
   mkdir -p data

5. （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効にする場合は環境変数で設定。

---

## 使い方（基本例）

以下はライブラリを直接インポートして使う際の代表的な例です。実行前に必ず必要な環境変数（特に API キー）をセットしてください。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、OPENAI_API_KEY 環境変数を設定
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", written_count)
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DuckDB を作成）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが初期化済み
```

- 研究用ファクター計算例:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
```

注意:
- score_news / score_regime は OpenAI API を使用します。API キー未設定時は例外が発生します。
- run_daily_etl は J-Quants API 呼び出しを行うため、JQUANTS_REFRESH_TOKEN が必要です。
- すべての処理は「ルックアヘッドバイアスを避ける」設計であり、target_date を明示して実行することを推奨します。

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主なモジュールの役割：
- config.py: 環境変数の読み込み・管理、Settings クラス
- data/jquants_client.py: J-Quants API クライアント + DuckDB への保存関数
- data/pipeline.py: ETL パイプライン（run_daily_etl 等）
- data/news_collector.py: RSS 収集と前処理
- ai/news_nlp.py: OpenAI を用いたニュースセンチメント評価
- ai/regime_detector.py: 市場レジーム判定ロジック
- research/*: ファクター計算・統計解析用ユーティリティ
- data/audit.py: 監査ログスキーマ定義と初期化ユーティリティ

---

## 開発・テスト時のヒント

- 自動 .env ロードはプロジェクトルート（.git/pyproject.toml を探索）から行われます。テスト時に .env を読み込ませたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API の呼び出し部分は内部で分離されており、ユニットテストではそれらの関数をモックする設計になっています（例: news_nlp._call_openai_api／regime_detector._call_openai_api を patch）。
- DuckDB を使ったテストは ":memory:" 接続や一時ファイルを利用してください。init_audit_db は親ディレクトリ自動作成、または ":memory:" をサポートします。
- ニュース RSS 取得では SSRF や gzip bomb 対策が施されています。外部リクエストを行うユニットテストでは fetch_rss/_urlopen をモックしてください。

---

## ライセンス / 貢献

本 README はソースコードからの機能説明に基づいて作成しました。実際のライセンス・貢献方法はリポジトリのトップレベルファイル（LICENSE、CONTRIBUTING.md 等）を参照してください。

---

必要であれば、README に「導入例スクリプト」「.env.example」の完全なテンプレートや、CI 用のテスト実行例、よくあるエラーと対処法（OpenAI レート制限、J-Quants トークン期限切れなど）を追加します。追加希望があれば教えてください。