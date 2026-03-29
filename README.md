# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）による市場データ収集、ニュースの収集・NLP スコアリング、ファクター算出、品質チェック、監査ログ（オーダー→約定トレーサビリティ）、および市場レジーム判定などを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ基盤とリサーチ / 自動売買を支える内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価日足、財務、マーケットカレンダー）
- ニュース収集（RSS）と前処理（URL 正規化、SSRF 対策など）
- OpenAI を使ったニュースのセンチメントスコアリング（銘柄別）とマクロセンチメントの評価
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック（欠損／重複／スパイク／日付不整合）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化
- 市場カレンダー管理（営業日判定・更新ジョブ）
- Kabuステーション等への実際の注文は別モジュールで実装想定（本パッケージは基盤・研究・監査の提供が主）

設計上の特徴：
- ルックアヘッドバイアス防止（target_date を明示して日次処理を行う設計）
- DuckDB を一次データベースに利用
- 冪等性（ON CONFLICT / idempotent 保存）
- ネットワーク系はリトライ・バックオフ・レート制御を実装
- テスト容易性のため外部コールを差し替え可能な実装（例: OpenAI 呼び出しのラッパー等）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 各種）
  - ニュース収集（RSS fetch、前処理、raw_news 保存）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - LLM 呼び出しは OpenAI（gpt-4o-mini）を想定。失敗時のフォールバックロジックあり。
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の自動ロード（.env / .env.local）と Settings オブジェクト
  - 自動ロードの無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- audit / monitoring / execution / strategy （パッケージ公開名には含まれているが、ここでは主に data/ai/research が実装済）

---

## セットアップ手順

前提
- Python 3.10+（Union/|注記、型表記から想定）
- DuckDB を使用するためネイティブ環境に問題がないこと

例：仮想環境の作成と依存インストール（パッケージ化されている場合は pyproject.toml / requirements.txt に従ってください）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml に従ってください）

3. パッケージを開発モードでインストール（リポジトリルートにて）
   - pip install -e .

4. 環境変数の設定
   - ルートに .env を置いて自動ロードさせるか、CI 等では環境変数として設定します。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース用ディレクトリ作成（必要であれば）
   - デフォルト duckdb_path は data/kabusys.duckdb（settings.duckdb_path を参照）

---

## 環境変数（主要）

Settings クラスや各モジュールが参照する主要な環境変数の例：

必須（多くの処理で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知用（必須プロパティとして定義されている）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu API を使う場合のパスワード（設定上必須）

任意 / デフォルト付き
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- OPENAI_API_KEY — OpenAI を利用する ai.score_news / ai.score_regime などで使用

.env の読み込み順序:
- OS 環境変数 > .env.local（override） > .env（override=False）
- .env のパースはシェル風（export あり、シングル/ダブルクォート、コメント処理）に対応

---

## 使い方（主要 API の例）

以下はライブラリの代表的な呼び出し例です。実行前に環境変数および DuckDB の設定を正しく行ってください。

1) Settings を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続して ETL を実行（1日分）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ（audit DB）初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

注意点：
- OpenAI 呼び出しには rate-limit リトライや JSON バリデーションの保護が入っていますが、API キーの有無や料金設定には注意してください。
- AI 評価のレスポンスは厳密な JSON を期待していますが、パースに失敗した場合はフォールバック値やスキップが行われます（例: macro_sentiment = 0.0）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - (他に schema / helpers 等が想定される)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py (上記)
- research/
  - factor_research.py, feature_exploration.py

主要モジュールの役割：
- kabusys.config: 環境変数と設定の読み込み・検証
- kabusys.data.jquants_client: J-Quants API との通信、取得／保存ユーティリティ
- kabusys.data.pipeline: 日次 ETL のオーケストレーション（run_daily_etl）
- kabusys.data.news_collector: RSS 取得と raw_news 用前処理
- kabusys.ai.news_nlp / regime_detector: OpenAI を使った NLP スコアリング
- kabusys.research: ファクター生成・評価ユーティリティ

---

## 開発・テストのヒント

- OpenAI の呼び出しは内部関数 _call_openai_api を使っており、ユニットテストでは monkeypatch / unittest.mock.patch によって差し替え可能です。
- .env 自動ロードがテストに影響する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して無効化できます。
- DuckDB の一時接続は ":memory:" を渡してインメモリ DB を使えます（audit.init_audit_db 等は ":memory:" をサポート）。

---

この README はコードベースからの要点をまとめたものです。詳細な API ドキュメントや利用ガイドは各モジュールの docstring を参照してください。追加で README に含めたい運用手順（CI / cron ジョブ設定例、Slack 通知設定、実際の発注フローなど）があれば教えてください。必要に応じて追記します。