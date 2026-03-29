# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（部分実装）。  
データETL、ニュースNLP、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

注意: このリポジトリはライブラリの一部を抜粋したコードベースです。実運用には各種テーブル定義・外部設定・依存ライブラリの導入が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化して提供します。

- J-Quants API を用いたデータ取得（株価日足・財務・マーケットカレンダー）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）および OpenAI によるニュースセンチメント解析
- 市場レジーム判定（ETF の MA とマクロニュースを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境設定管理（.env 自動読み込み、必須設定の検証）

設計方針として、ルックアヘッドバイアス回避（date の明示指定）、DuckDB を利用した効率的な SQL 処理、外部 API 呼び出しの冪等性とリトライ制御を重視しています。

---

## 機能一覧（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート判定: `.git` または `pyproject.toml`）
  - 必須環境変数の取得（settings オブジェクト経由）
  - 自動読み込み無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- kabusys.data
  - jquants_client: J-Quants API ラッパー（認証・ページネーション・保存関数）
  - pipeline: 日次 ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - news_collector: RSS 収集（SSRF 対策、前処理、冪等保存想定）
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブルの初期化 / DB 作成ヘルパー

- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離と LLM マクロセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize: 汎用 Z スコア正規化

---

## セットアップ手順

以下はローカルで開発・実行するための一般的な手順例です。

1. リポジトリをクローンし、仮想環境を作成・有効化する
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要な依存パッケージをインストールする（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは `requirements.txt` / `pyproject.toml` に合わせてインストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI 呼び出し用（AI 機能を使う場合）
   - 任意 / デフォルト値あり
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動読み込み無効化フラグ
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例: `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下は主要 API の使い方サンプルです。DuckDB 接続は `duckdb.connect(path)` を使用します。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化（OpenAI API キーが環境変数にある想定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（1321 の MA200 とマクロニュースの LLM スコアを合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- 環境設定を取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

テスト時のヒント:
- OpenAI 呼び出しはモジュール内の `_call_openai_api` 関数を patch してモックできます。
  例: `unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", ...)`
- `.env` の自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースに含まれる主要モジュールの階層（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース再エクスポート
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー

（実際のリポジトリにはさらにユーティリティや schema 定義などが存在する可能性があります）

---

## 注意事項 / 補足

- Look-ahead バイアス防止:
  - 多くの関数は内部で `date.today()` や `datetime.today()` に依存せず、明示的な `target_date` を受け取る設計です。バックテストや再現性のために日付を明示してください。

- 冪等性・トランザクション:
  - ETL / 保存処理は可能な限り冪等に設計されています（ON CONFLICT / DELETE → INSERT の使用など）。
  - 一部の初期化関数は transactional オプションを持ちます（例: init_audit_schema）。

- 外部 API / レート制限:
  - J-Quants: 固定レート制限 (120 req/min) を守るための RateLimiter を実装済み。
  - OpenAI: JSON Mode を使った厳格なレスポンス想定。429 / ネットワーク断 / 5xx に対してリトライ実装あり。

- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査・プライベートアドレス拒否）や XML 攻撃対策（defusedxml）を行います。
  - HTTP ヘッダやレスポンスサイズの上限チェックを実装しています。

---

必要であれば、この README をベースに「デプロイ手順」「スキーマ定義（CREATE TABLE）」「CI 用のテスト実行手順」「サンプル .env.example」などを追加で作成できます。どの項目を優先しますか？