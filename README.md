# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。J-Quants から市場データを取得して DuckDB に永続化し、ニュースの NLP による銘柄スコアリング、マーケットレジーム判定、ファクター計算、ETL パイプライン、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「DB（DuckDB）中心の永続化」「外部 API 呼び出しはフェイルセーフで継続」「テスト可能性の確保（依存注入／差し替え可能）」です。

バージョン: 0.1.0

---

## 機能一覧

- 設定・環境変数管理
  - `.env` / `.env.local` 自動ロード（必要に応じて無効化可能）
  - 必須設定の取得（J-Quants / kabuステーション / Slack 等）
- データ ETL（J-Quants 統合）
  - 日次株価（raw_prices）、財務（raw_financials）、市場カレンダー（market_calendar）取得・保存
  - 差分取得・バックフィル・ページネーション対応・リトライ・レート制御
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集・NLP スコアリング
  - RSS フィード収集（SSRF 対策、gzip 上限、トラッキング除去）
  - OpenAI (gpt-4o-mini) による銘柄別センチメント（ai_scores への書込み）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを持つ監査スキーマの初期化・管理
  - 発注の冪等キー管理（order_request_id）
- J-Quants クライアント
  - トークン取得（リフレッシュ）、日次株価・財務・カレンダー等の取得
  - DuckDB へ冪等保存（ON CONFLICT 相当）
  - レート制御（120 req/min）・リトライ・401 自動リフレッシュ対応

---

## セットアップ手順

前提: Python 3.9+（タイプヒントやモジュール動作に応じて必要なバージョンを合わせてください）

1. リポジトリをクローン、パッケージをインストール（開発中の場合は editable）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install -e ".[dev]"     # requirements を setup.py/pyproject に合わせてインストール
   ```
   ※ ここでは必要な主要パッケージを例示します:
   - duckdb
   - openai
   - defusedxml

   必要に応じて pyproject.toml / requirements.txt を参照して依存をインストールしてください。

2. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を配置すると、自動的に読み込まれます（ただしテスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。
   - 必須の環境変数（少なくとも以下は設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必要な場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知チャネル
     - OPENAI_API_KEY — OpenAI を使う機能（news/regime）を使う場合（ai 関連）
     - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DB パスのデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB 用ディレクトリを作成（デフォルト）
   ```
   mkdir -p data
   ```

---

## 使い方（主要なユースケース例）

下記はコードから直接利用する際の簡単な例です。必要に応じてスクリプトや CLI を作成して運用してください。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # today を明示的に渡すことでテストしやすくなる
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（OpenAI API キーが環境変数または引数で必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を参照
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用専用 DB を作る）
  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  # これで signal_events / order_requests / executions テーブルが作成される
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)

  # Zスコア正規化
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- ニュース収集（RSS）を直接呼ぶ（例）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

---

## 設定と注意点

- 環境変数自動ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば `.env` と `.env.local` を自動的に読み込みます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env は上書きされないが .env.local は上書きします）。
- ログレベル・環境
  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかで、settings.is_live 等で判定できます。
  - LOG_LEVEL は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれか。
- OpenAI
  - news_nlp / regime_detector は OpenAI の Chat Completions（gpt-4o-mini を想定）を使います。API キーは `OPENAI_API_KEY` で与えるか、関数呼び出しの `api_key` 引数で渡します。
  - API 呼び出しは冗長にリトライ・フェイルセーフが組み込まれており、失敗時は影響を限定するよう設計されています（スコアを 0.0 にフォールバックする等）。
- J-Quants
  - J-Quants のリフレッシュトークンは `JQUANTS_REFRESH_TOKEN` に設定してください。モジュールは必要時に ID トークンを取得しキャッシュします。
  - API のレート制御（120 req/min）は内部で行われます。
- RSS / ニュース収集
  - SSRF や XML Bomb、過大レスポンスに対する防御（リダイレクト検証／プライベート IP ブロック／受信上限／defusedxml）を実装しています。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールとその目的（src/kabusys 以下）です:

- kabusys/
  - __init__.py
  - config.py — 環境変数とアプリ設定（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — マクロセンチメント + MA200 乖離で market_regime を算出
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理・DB 保存ヘルパー
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py — 監査ログスキーマ作成・init (signal_events/order_requests/executions)
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

（実際のファイル構成はリポジトリの src/kabusys 以下を参照してください）

簡易ツリー例:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## よくある運用フロー（例）

- 毎朝（深夜バッチ）:
  - run_daily_etl を実行して市場カレンダー・株価・財務データを更新
  - quality.run_all_checks を実行してデータ品質を検査、通知（Slack 連携など）
- 記事到着後（定期）:
  - news_collector.fetch_rss → raw_news に保存 → news_nlp.score_news で ai_scores を更新
- トレーディング前:
  - research のファクターを計算してランキング、position sizing 用の信号生成
  - strategy 層で signal を生成し order_requests 経由で発注（監査ログに残す）
- 発注 / 約定時:
  - executions テーブルに約定を記録しトレーサビリティを確保

---

## テスト・開発上のヒント

- 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてからテストを行うとローカル環境に依存しないテストが可能です。
- OpenAI 呼び出しや外部 API 呼び出しは各モジュール内部の _call_openai_api や data の HTTP 関数をモックしやすい設計になっています（unittest.mock.patch 等）。
- DuckDB はインメモリ(":memory:") 接続が可能なのでユニットテスト時はファイルを作らずにテストできます。

---

必要ならば README に以下を追記できます:
- 具体的な .env.example、DB スキーマ定義の抜粋
- CI / デプロイ手順（systemd / cron / Airflow などとの組合せ例）
- より詳細な API 使用例（news_nlp/regime_detector の出力仕様）
ご希望があれば追記します。