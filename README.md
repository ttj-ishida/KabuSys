# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントは、プロジェクトの概要、機能、セットアップ、主要な使い方およびディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量生成（ファクター計算）、ニュースの NLP スコアリング、ならびに監査ログ設計までを包含する汎用ライブラリです。  
主に次の用途を想定しています。

- J-Quants API から日次株価・財務・カレンダーを差分取得して DuckDB に保存（ETL）
- ニュース記事の収集・前処理・LLM を用いた銘柄別センチメント評価
- 市場レジーム判定（ETF MA と LLM センチメントの合成）
- 研究用途のファクター計算・将来リターン計算・IC（Information Coefficient）算出
- 発注・約定までを辿る監査ログ（audit）スキーマの初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合等）

設計上のポイント:
- ルックアヘッドバイアス防止を重視（内部で datetime.today() を直接使わない等）
- DuckDB を中心に SQL / Python を組合せて高速に処理
- 外部 API 呼び出しはフェイルセーフなフォールバック（エラー時に処理継続）
- 冪等性を重視した DB 書き込み（ON CONFLICT 等）

---

## 主な機能一覧

- 環境設定管理
  - 自動 .env 読み込み（プロジェクトルート基準、.env.local 優先）
  - 必須環境変数取得時の検証
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl を使った日次 ETL（株価 / 財務 / カレンダー）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット対応、リトライ、トークン自動リフレッシュ
  - fetch / save の API（daily_quotes, financial_statements, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、安全対策（SSRF 回避、gzip/サイズ上限、XML 安全パーサ）
  - 前処理（URL 除去・空白正規化）と記事 ID 正規化（SHA-256）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコアリング
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントの重み合成
  - DuckDB への冪等書き込み
- 研究用モジュール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema による初期化

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型表記などを使用）
- 仮想環境の利用を推奨

例：

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   - 必要な外部パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - pip を用いる例:
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt / pyproject.toml があればそれを使用
   ```

3. パッケージを開発モードでインストール（プロジェクトが pyproject.toml/setup 配下の場合）
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須（本番的に必要なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
   - OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定）
   - KABU_API_PASSWORD — kabu API パスワード（発注用; present but not used in shown code）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack 情報（任意の通知実装）

   その他（デフォルトがあるもの）:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）

   例 `.env`（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DB 初期化（監査ログなど）
   - 監査用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（簡易サンプル）

以降の例は Python REPL / スクリプトから実行することを想定します。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略すると今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（ai_scores）を算出
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数にある場合は api_key を省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出し系（news_nlp, regime_detector）は API キーを取るため、api_key 引数に直接渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API は JQUANTS_REFRESH_TOKEN を元に id_token を取得します（settings.jquants_refresh_token）。
- ETL / API 呼び出しは可能な限りリトライ・フェイルセーフを組み込んでいますが、API クォータ制限やネットワーク状態に依存します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの重要なモジュールを抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch / save）
    - pipeline.py            # ETL パイプラインと run_daily_etl
    - stats.py               # zscore_normalize 等の統計ユーティリティ
    - quality.py             # データ品質チェック
    - news_collector.py      # RSS 収集と前処理
    - calendar_management.py # マーケットカレンダーヘルパー（is_trading_day 等）
    - audit.py               # 監査ログ（テーブル定義・初期化）
    - etl.py                 # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # 将来リターン / IC / 統計サマリー 等

---

## 実運用上の注意・補足

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動ロードします。
  - 優先順位: OS 環境 > .env.local > .env
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env のパースはシェル風の export やクォート、インラインコメントに対応しています。

- OpenAI / J-Quants 呼び出し
  - LLM 系の API 呼び出しはレスポンス検証とリトライを実装していますが、過度な同時呼び出しは避け、API 単位でのレート制御を行ってください。
  - J-Quants はレート制限を守るため内部でスロットリングを行います。

- DuckDB への大量 INSERT 等は executemany を使用しています。DuckDB のバージョンの差異により挙動が変わる場合があるため、DuckDB を最新安定版に揃えることを推奨します。

- テスト・モック
  - news_nlp/_call_openai_api や regime_detector/_call_openai_api などはユニットテストで差し替え（patch）しやすい設計になっています。

---

この README は基本的な導入と利用法をまとめたものです。詳細な仕様（API のパラメータ、ETL の細かい動作、SQL スキーマの完全仕様など）は各モジュールの docstring を参照してください。必要であれば、より具体的な使用例や運用手順（デプロイ、cron / CI 設定、監視設計）を追記しますので要望をお知らせください。