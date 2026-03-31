# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants）によるデータ収集、ニュースのNLPスコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、バックテスト／運用に必要な機能群を提供します。

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、上場情報、JPXカレンダー等の差分取得と DuckDB への冪等保存
  - ETL の品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・NLP
  - RSS からの安全なニュース収集（SSRF 対策、トラッキング除去、サイズ上限）
  - OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄別センチメント評価（ai_scores への書き込み）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLMセンチメントを合成して daily market_regime を判定
- リサーチ（ファクター）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定までトレース可能な監査スキーマ（DuckDB）
  - 冪等（order_request_id）・ステータス管理を想定
- 設定管理
  - .env / .env.local / OS 環境変数からの自動ロード（プロジェクトルート検出）
  - 実行環境（development / paper_trading / live）とログレベルの検証

---

## 必要要件

- Python 3.10+
- 依存ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI 等の API）

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主なもの）

以下は本ライブラリで参照される主な環境変数の例です。`.env` に設定しておくと自動で読み込まれます（.env.local は上書き）。

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に使用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（使用する場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必要な場合）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

自動 .env ロードを無効にするには:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   - git clone ...
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
     （実プロジェクトでは pyproject.toml / requirements.txt に従ってください）
4. .env を作成
   - リポジトリルートに .env を置くと自動で読み込まれます（.env.local は上書き）
   - 例（最低限）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxxx
     - SLACK_BOT_TOKEN=x
     - SLACK_CHANNEL_ID=C01234567
5. DuckDB 用ディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（主要な API と実行例）

以下はライブラリの主要な関数の使い方例です。実際はアプリケーション用のラッパー CLI やジョブスケジューラから呼び出します。

- DuckDB 接続準備例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は today
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（AI による銘柄別センチメント）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # conn: DuckDB 接続
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う場合は None
  print(f"written {written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルに永続化する場合
  audit_conn = init_audit_db("data/audit.duckdb")
  # またはインメモリ:
  # audit_conn = init_audit_db(":memory:")
  ```

- 研究用 API（ファクター計算など）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  ```

注意:
- score_news / score_regime は OpenAI の API を呼び出します。APIキーは api_key 引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL は J-Quants API を呼び出します。J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）を設定してください。

---

## 開発・テストのヒント

- 環境変数の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定しておくとユニットテストが安定します。
- OpenAI 呼び出し部分は内部で _call_openai_api を経由しているため、テスト時は該当関数をモック（unittest.mock.patch）して外部 API 呼び出しを抑制できます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp)
- RSS フィード取得では defusedxml を利用し XML 爆弾等の攻撃に備えています。ネットワーク依存テストはモック推奨。
- DuckDB に対する executemany の挙動（空リストが許されない等）に注意している箇所があります。テストデータ作成時は注意してください。

---

## ディレクトリ構成（抜粋）

パッケージの主要なファイル構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースのNLPスコアリング（OpenAI）
    - regime_detector.py   # 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py   # 市場カレンダー管理・営業日ロジック
    - pipeline.py              # ETL パイプライン / run_daily_etl
    - jquants_client.py        # J-Quants API クライアント + 保存関数
    - news_collector.py        # RSS 収集（SSRF対策、前処理）
    - quality.py               # 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 # 共通統計ユーティリティ（z-score 等）
    - audit.py                 # 監査ログ（テーブル定義・初期化）
    - etl.py                   # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       # ファクター計算（Momentum, Value, Volatility）
    - feature_exploration.py   # 将来リターン・IC・サマリー等
  - ai/ (上記)
  - research/ (上記)
  - その他: strategy / execution / monitoring（package として __all__ に含める想定）

（README は主要モジュールを中心に抜粋しています。実プロジェクトではさらに CLI や webhooks、execution ブリッジ等が存在する可能性があります）

---

## 運用上の注意

- 実口座での運用を行う場合は必ず "live" 環境フラグ（KABUSYS_ENV=live）を設定し、十分なテスト（paper_trading 環境）を行ってください。
- 発注・監査ロジックは冪等性（order_request_id）やエラーステータス管理を前提としていますが、実ブローカー連携時は二重発注や例外ケースの確認を厳密に行ってください。
- OpenAI 呼び出しや外部 API 呼び出しにはコストとレート制限があるため、ジョブ運用時はスロットリング・リトライ方針（実装済み）を考慮してください。

---

不明点や README に追記してほしい項目（例: 実行例の CLI、追加の環境変数一覧、db スキーマ定義の詳細等）があれば教えてください。README を目的（開発者向け / 運用者向け / ユーザー向け）に合わせて調整します。