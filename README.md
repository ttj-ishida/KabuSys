# KabuSys

KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買支援ライブラリです。J-Quants API からデータを取得して DuckDB に保存し、ニュースの NLP スコアリングや市場レジーム判定、ファクター計算、ETL パイプライン、監査ログ（トレース）の初期化などを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API 失敗は局所的に処理を続行）」で、DuckDB を中核に据えたローカルデータパイプラインと研究用ユーティリティ群を備えます。

---

## 主要機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務情報、上場情報、JPX マーケットカレンダーを差分取得・保存（jquants_client, data.pipeline）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合などの検出と QualityIssue レポート
- ニュース収集・前処理（data.news_collector）
  - RSS フィードから記事を取得・正規化・保存（SSRF 対策・追跡パラメータ除去）
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント生成（ai_scores に書き込み）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200日移動平均乖離とマクロニュース LLM センチメントを合成して market_regime に記録
- 研究用ユーティリティ（research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC（スピアマン）計算、Zスコア正規化など
- 監査ログ（data.audit）
  - シグナル → 発注要求 → 約定までをトレース可能にする監査スキーマの初期化ユーティリティ
- 設定管理（config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）と Settings クラスによる環境変数ラップ

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（型注釈で Python 3.10 機能を使っている箇所があるため 3.10 以上が望ましい）
- DuckDB、OpenAI SDK、defusedxml 等が必要

1. リポジトリをクローン／ダウンロード
   - 例: git clone <repo-url>

2. 開発環境にパッケージをインストール（プロジェクト直下で）
   - 推奨: 仮想環境を作成して有効化する
   - pip を使う例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # (Windows) .venv\Scripts\activate
     pip install -U pip
     pip install duckdb openai defusedxml
     pip install -e .
     ```
   - 依存パッケージはプロジェクトの setup/pyproject に基づいて適宜追加してください。

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack Bot トークン（モニタリング用）
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト localhost）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベースディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以降の例は Python REPL / スクリプト内で実行できます。事前に必要な環境変数をセットしてください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア生成（ai.news_nlp.score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定済みであること
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへアクセスできます
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト（date, code, mom_1m, mom_3m, ...）
  ```

- ニュース RSS のフェッチ（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(src, source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しを伴う処理（score_news, score_regime）は API 利用料・レート制限に注意し、環境変数 OPENAI_API_KEY を設定してください。関数は API 失敗時にフェイルセーフ（スコア0等）で継続する設計です。
- run_daily_etl などは外部 API の呼び出しを行うため、ネットワーク環境とトークンの準備が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は本コードベースの主要モジュール（src/kabusys 以下）の構成です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 呼び出し, ai_scores に保存）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存関数）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集・前処理
    - calendar_management.py  — 市場カレンダーの管理・営業日ユーティリティ
    - quality.py              — データ品質チェック（QualityIssue）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー等
  - research/*                — 研究用ユーティリティ群

- その他
  - pyproject.toml / setup.cfg 等（パッケージ定義）
  - .env.example（存在する場合は参照して .env を作成）

---

## 開発・運用上の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の空リスト渡しは一部バージョンの制約があるため、コード側で空チェックを行っています（互換性配慮）。
- OpenAI 関連の呼び出しは retry/backoff を備えていますが、API 料金に注意して使用してください。
- 監査ログ（audit）には UTC タイムゾーンを固定して保存します。init_audit_schema は TimeZone を UTC に設定します。
- コードはルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を直接参照しない設計が多く取り入れられています（関数引数で日付を注入可能）。

---

必要に応じて README の実行例や API 使用方法を追加できます。特定の操作（ETL トラブルシュート、OpenAI 呼び出しのモック方法、DB スキーマ確認など）について詳述したい場合は教えてください。