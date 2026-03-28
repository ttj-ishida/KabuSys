# KabuSys

KabuSys は日本株のデータパイプライン、AI を使ったニュースセンチメント解析、リサーチ（ファクター計算）、
ならびに監査ログ（オーディット）やカレンダー管理を備えた自動売買システムのコアライブラリです。
このリポジトリはデータ取得（J-Quants）、ETL、品質チェック、ニュース収集・NLP、レジーム判定、研究用ユーティリティを提供します。

## 主な特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存
  - DuckDB を用いた冪等保存（ON CONFLICT / DO UPDATE）
  - daily ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで問題を収集・報告
- ニュース収集（RSS）
  - RSS フィード取得時の SSRF 対策、トラッキング除去、前処理、raw_news への冪等保存（ID=URLハッシュ）
- ニュースNLP（OpenAI）
  - 複数銘柄をバッチ処理して記事群から銘柄ごとのセンチメント（-1.0～1.0）を生成し ai_scores に書き込み
  - リトライ、レスポンス検証、トークン肥大対策、JSON mode を使った堅牢な実装
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321（日経225連動）200日MA乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    日次で market_regime を判定（bull / neutral / bear）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）、Zスコア正規化、統計サマリー
- 監査ログ（オーディット）
  - signal_events / order_requests / executions テーブルとインデックス定義、冪等初期化関数を提供

## セットアップ手順

前提: Python 3.10+（型ヒントで Union 表現などを使用）、DuckDB、OpenAI SDK 等を用います。

1. リポジトリをクローン / 作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   - パッケージ管理ファイルがある場合はそれを利用してください（例: pyproject.toml / requirements.txt）。
   - 最低限の依存（明示的）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（プロジェクトパッケージが正しくパッケージ化されている場合）:
     ```bash
     pip install -e .
     ```

4. 環境変数の設定
   - 本ライブラリは環境変数あるいは .env/.env.local から設定を読み込みます（config.Settings）。
   - .env をプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）に置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須 / 推奨環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu API パスワード（kabuステーション連携用）
     - SLACK_BOT_TOKEN (必須) — Slack 通知用（使用箇所がある場合）
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp, regime_detector 等）に使用（関数呼び出し時に引数で渡すことも可）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

## 使い方（代表的な API と例）

以下は典型的な利用例です。各関数は DuckDB の connection オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（ai_scores へ書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定しておくか api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は内部で呼ばれ、必要なテーブル・インデックスが作成されます
  ```

- RSS フィードを取得する（ニュース収集の低レイヤー）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意事項:
- OpenAI を使う処理（news_nlp, regime_detector）は API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / データ書き込みは冪等性（ON CONFLICT）を考慮した実装になっていますが、実行前にスキーマ（raw_prices など）を準備しておく必要があります（スキーマ初期化関数が別途存在する場合があります）。
- 各処理は基本的に「ルックアヘッドバイアス」を避ける設計（target_date 未満のデータのみ参照する等）になっています。バックテスト等で使う際はその点に留意してください。

## ディレクトリ構成（主要ファイルの概要）
以下は src/kabusys 以下の主要モジュールと役割です。

- kabusys/
  - __init__.py
    - パッケージ初期化・公開モジュール定義
  - config.py
    - 環境変数読み込み、Settings クラス（設定アクセス）
    - .env 自動読み込み機能（.git または pyproject.toml を基準にプロジェクトルートを検出）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事群を LLM で解析し ai_scores へ書き込む処理
    - regime_detector.py
      - ETF MA とマクロニュース LLM を組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、取得、DuckDB への保存関数）
    - pipeline.py
      - ETL の上位制御（run_daily_etl など）と ETLResult
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - news_collector.py
      - RSS 取得、前処理、記事ID生成、SSRF 対策
    - calendar_management.py
      - JPX カレンダー管理、営業日判定ユーティリティ
    - stats.py
      - zscore 正規化などの統計ユーティリティ
    - etl.py
      - ETL インターフェースの再エクスポート
    - audit.py
      - 監査ログ（signal / order / executions）テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム、ボラティリティ、バリューなどのファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク付けなど

各モジュールは docstring に詳細な設計方針・処理フロー・フォールバック挙動が書かれているため、
実装を追うことで具体的な挙動を理解しやすくなっています。

## 開発・テスト時のヒント
- 自動 .env 読み込みが不要なユニットテストでは、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク依存処理はテスト時にモックしやすいよう設計されています（内部関数を patch 可能）。
- DuckDB はメモリ接続（":memory:"）でテスト可能です。init_audit_db なども ":memory:" を受け付けます。

---

README の内容はコードベースの現状をもとに作成しています。実行環境や追加の運用スクリプト（デーモン、CI、schema 初期化スクリプト等）がある場合は、それらの手順を別途ドキュメント化することを推奨します。必要であればサンプル .env.example、setup.py/pyproject.toml の README 追記、あるいは具体的な起動スクリプト例も作成しますのでお知らせください。