# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、外部 API クライアント（J‑Quants / OpenAI / kabuステーション）との連携ロジックを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとそれを支えるデータ基盤のためのモジュール群です。主に以下を提供します。

- J‑Quants API を使った株価 / 財務 / 市場カレンダーの差分 ETL と DuckDB への保存
- raw_news の収集・前処理・銘柄紐付け（RSS ベース）とニュースの NLP（OpenAI）による銘柄センチメント評価
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究・リサーチ用のファクター計算（Momentum / Volatility / Value 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用のスキーマ初期化ユーティリティ

設計方針として「ルックアヘッドバイアス防止」「冪等性」「堅牢な API リトライ」「テスト可能性」を重視しています。

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J‑Quants クライアント（fetch / save / 認証・自動リフレッシュ、レート制御）
  - market calendar 管理 / 営業日判定ユーティリティ
  - news_collector（RSS 取得、SSRF 対策、前処理）
  - quality（データ品質チェック）
  - audit（監査ログスキーマの初期化 / 専用 DB 作成）
  - stats（zscore 正規化等）
- ai:
  - news_nlp.score_news（銘柄ごとのニュースセンチメントを ai_scores に書き込む）
  - regime_detector.score_regime（市場レジーム判定を market_regime に書き込む）
- research:
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - Settings（環境変数ベースの設定取得、自動 .env ロード機能）

---

## 必要な環境変数

必須（実行する機能により必要なもの）:

- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（jquants_client.get_id_token 等で使用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合
- KABU_API_PASSWORD — kabuステーション API を使う場合

オプション / デフォルトあり:

- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / ai.regime_detector で利用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env の自動ロード挙動:

- 実行時、プロジェクトルート（.git または pyproject.toml を探索）から自動で `.env` と `.env.local` を読み込みます。
  - 読み込み優先度: OS 環境変数 > `.env.local` > `.env`
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風の `export KEY=val`、クォート、コメント（行頭＃と値側の # が直前に空白/タブであればコメント扱い）に対応しています。

---

## セットアップ手順（例）

前提: Python 3.10 以上を推奨（PEP 604 の Union 型 (|) 等を使用）

1. リポジトリをクローン / パッケージを配置
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要なパッケージをインストール
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 例: pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）
4. 環境変数をセット
   - 例: プロジェクトルートに `.env` を作る（.env.example に従う）
   - 例（最小）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
5. DuckDB 用ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（主な API / 例）

以下は基本的な利用例です。すべて Python コード内から呼び出します。

- ETL（日次 ETL）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（OpenAI 必須）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # 必要なディレクトリは自動作成
  ```

- news_collector: RSS 取得（単体呼び出し）

  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["title"], a["datetime"], a["url"])
  ```

注意点:
- OpenAI 呼び出しはネットワーク/レート/JSON パース失敗時にフェイルセーフで 0.0 やスキップする実装になっています（例外が全て投げられるわけではありません）。ログを確認してください。
- J‑Quants API は ID トークンを内部キャッシュし、401 発生時に自動リフレッシュして一度だけリトライします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py — Settings, .env 自動読み込み、必須 env チェック
  - ai/
    - __init__.py
    - news_nlp.py — news の LLM スコアリングと ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定（MA + マクロ LLM）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - etl.py — ETL 結果型エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — zscore_normalize 等汎用統計
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ定義 / 初期化
    - jquants_client.py — J‑Quants API クライアント（fetch/save/認証）
    - news_collector.py — RSS 収集（SSRF / Gzip / トラッキング除去 等）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value の算出
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 開発 / テストに関する注意

- 設計では「ルックアヘッドバイアス防止」を徹底しており、target_date 引数を使って戻り値が決まるようになっています。datetime.today() の直接参照は避けられているため、バックテスト等で deterministic に動作させやすいです。
- テストしやすいように OpenAI / ネットワーク呼び出し部分は個別関数を経由しており、unittest.mock.patch による差し替えが可能です（news_nlp._call_openai_api 等）。
- .env 自動ロードを無効化することでテスト環境での副作用を抑止できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ログとデバッグ

- Settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 各モジュールは logger を用いて詳細な INFO/WARNING/ERROR を出力します。問題発生時はログを確認してください。

---

## ライセンス / 貢献

リポジトリ内に LICENSE があればそれに従ってください。外部 API（J‑Quants / OpenAI / kabuステーション）利用にあたってはそれぞれの利用規約やレート制限に従ってください。

---

必要であれば README に以下を追加できます：
- 例の .env.example 内容
- requirements.txt の推奨リスト
- 具体的な CI / デプロイ手順
- API 利用時の注意（コスト・レート制限の具体値）