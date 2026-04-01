# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、ファクター研究、監査ログ（発注→約定のトレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は、以下を安全かつ再現可能に実現することです。

- J-Quants API からのデータ取得（株価、財務、JPX カレンダー）
- DuckDB を用いたデータ保存と ETL パイプライン
- RSS ニュース収集と OpenAI（gpt-4o-mini）を使った記事／マクロセンチメントのスコアリング
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー 等）
- 監査ログ用スキーマ（signal -> order_request -> execution の追跡）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴:
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等性（DB 保存は ON CONFLICT による上書きを想定）
- API リトライ・レート制御・フェイルセーフ（失敗時はスキップして継続する箇所がある）
- 外部依存は最小限（主要処理は DuckDB + 標準ライブラリ + 必要な外部ライブラリ）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS → raw_news, SSRF 対策・トラッキング削除）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを合成し market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理
  - kabusys.config.settings: 環境変数/.env からの設定読み込み（自動ロード、無効化フラグあり）

---

## 必要条件（主な依存）

主なランタイム依存（実行環境に応じて適宜インストールしてください）:

- Python 3.9+
- duckdb
- openai
- defusedxml

インストール例（プロジェクトルートで）:
- pip install -e . もしくは requirements.txt を用意している場合は pip install -r requirements.txt

（本リポジトリに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

---

## 環境変数 / .env

このパッケージは .env ファイル（プロジェクトルート）や OS 環境変数から設定を読み込みます。自動ロードはデフォルトで有効（プロジェクトルートは .git または pyproject.toml により判定）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL の認証に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で利用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（注文関連がある場合）
- SLACK_BOT_TOKEN: Slack 通知用の Bot トークン（通知実装がある場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

任意／デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視など）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT などの監視設定

.env のパースはシェルライクな形式に対応（export プレフィックス、クォート、コメント除去など）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e . 
     または
   - pip install duckdb openai defusedxml

4. .env を作成
   - プロジェクトルートに .env を作成し、必須キーを設定します（例）:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
     - その他オプション設定を必要に応じて追加

   自動ロードを使いたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は主要 API の利用例（Python スクリプト内で実行）。

- DuckDB 接続を作成して ETL を走らせる例:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数に設定済みの前提）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB）:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以後 conn を使って監査テーブルへ書き込み／クエリ可能
```

- 研究用ファクター計算:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意:
- OpenAI 呼び出し関数は api_key 引数を受け取れる場合があります（env を使いたくない場合は明示的に渡してください）。
- 多くの処理は DB 内の該当テーブル（raw_prices, raw_financials, raw_news, news_symbols, market_regime, ai_scores 等）を参照します。初回は ETL によりテーブルが作成・投入されることを想定しています。

---

## 主要 API の説明（抜粋）

- kabusys.config.settings: .env / 環境変数から設定を取得（プロパティ経由）
- kabusys.data.pipeline.run_daily_etl(...): 日次 ETL のメインエントリ。ETLResult を返す。
- kabusys.data.jquants_client: J-Quants との通信・保存処理（fetch_* / save_*）。
- kabusys.data.news_collector.fetch_rss(url, source): RSS フィードの取得・前処理ユーティリティ。
- kabusys.ai.news_nlp.score_news(conn, target_date): ニュース → ai_scores 書き込み。
- kabusys.ai.regime_detector.score_regime(conn, target_date): market_regime 書き込み。
- kabusys.research.factor_research.calc_momentum/…: ファクター計算。
- kabusys.data.quality.run_all_checks(...): データ品質チェック全実行。
- kabusys.data.audit.init_audit_schema / init_audit_db: 監査スキーマ初期化。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースNLPスコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS 収集・前処理（SSRF 対策等）
    - calendar_management.py        — 市場カレンダー管理
    - stats.py                      — zscore_normalize 等
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility
    - feature_exploration.py        — calc_forward_returns, IC, summary 等
  - ai/ etc. (上記)

---

## 運用上の注意

- OpenAI や J-Quants は課金・レート制限があるため、運用時は API キーの管理・レートの考慮が必要です。jquants_client では固定間隔スロットリングを行っていますが、実行環境の負荷や API 制限に応じて設定を調整してください。
- 自動ロードされる .env に機密情報（API キー等）が含まれるため、バージョン管理には含めないでください。
- ETL と AI 呼び出しは外部 API に依存するため、ユニットテスト時には network 呼び出しをモックすることを推奨します。コード中にモック用の差し替えポイント（_call_openai_api の patch 等）が用意されています。
- DuckDB の executemany に関する互換性注意（空リスト渡し不可）など、コメントとして実装上の制約があります。ライブラリ内部で既に考慮されています。

---

## サポート / 開発

- バグ報告や改善提案は Issue にてお願いします。
- ローカルでの開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みが無効化されるためテストが容易になります。

---

この README はリポジトリに含まれる主要機能・使い方の概要をまとめたものです。詳細は各モジュールの docstring（src/kabusys/**/*.py）をご参照ください。