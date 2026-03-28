# KabuSys

日本株向け自動売買・データプラットフォームのコアライブラリ（KabuSys）。  
データ取り込み（J-Quants）、ニュース収集・NLP、研究用ファクター計算、監査ログ、ETL パイプライン、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象としたデータ基盤と研究 / 戦略用ユーティリティを集めた Python パッケージです。主要な機能は次の領域をカバーします。

- データ取得・ETL（J-Quants API 経由の株価・財務・カレンダー）
- ニュース収集（RSS）とニュースの NLP（OpenAI を利用したセンチメント評価）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック
- 監査ログ（シグナル→発注→約定のトレース用テーブル）
- カレンダー管理（営業日判定・次営業日/前営業日取得）

設計上、ルックアヘッドバイアスに注意した日付取り扱いや、ETL の冪等性、外部 API のリトライ/レート制御、フェイルセーフな振る舞いが組み込まれています。

---

## 機能一覧（抜粋）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - 各種必須設定取得ラッパー（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制限、リトライ、データ保存）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ
  - news_collector: RSS 収集（SSRF対策、正規化、DB への冪等保存）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログスキーマの初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM スコアを合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

※ 以下は典型的なセットアップ手順です。プロジェクトに合わせて適宜修正してください。

1. Python 環境の作成（推奨: venv / pyenv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. インストール（必要なパッケージをインストール）
   - 必要な外部依存の例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発・パッケージ配布を想定する場合はプロジェクトルートで:
     ```
     pip install -e .
     ```
     （プロジェクトに requirements/pyproject があればそちらを利用）

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - SLACK_BOT_TOKEN：Slack 通知に使用する Bot トークン（必須）
     - SLACK_CHANNEL_ID：Slack のチャンネル ID（必須）
     - KABU_API_PASSWORD：kabuステーション API パスワード（必須：発注機能使用時）
     - OPENAI_API_KEY：OpenAI を使用する機能（news_nlp / regime_detector）を動かす場合に必要
     - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（任意、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
   - サンプル .env（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベースディレクトリ作成
   - DUCKDB_PATH の parent ディレクトリが存在しない場合は作成してください（多くの初期化関数は自動作成しますが事前準備しておくと安心です）。

---

## 使い方（簡単な例）

以下はライブラリを直接 Python から利用する際の代表的な例です。実運用では適切なエラーハンドリング・ログ設定を行ってください。

- DuckDB 接続の作成と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定（省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai_scores への書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

---

## 自動環境読み込みの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば、ルートの `.env` と `.env.local` を読み込みます（OS 環境変数の上書きはデフォルトで行われません。`.env.local` は上書き）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル一覧（コードベースの例）です。

- src/kabusys/
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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: pipeline で使う quality/jquants_client の補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (上記)
  - research/ (上記)
  - その他モジュール: strategy / execution / monitoring （パッケージ公開リストに含まれるがここには最小限の実装がない場合あり）

※ 実際のリポジトリでは tests/, docs/, scripts/ 等の補助ディレクトリが存在する場合があります。

---

## 注意点 / 運用上のヒント

- OpenAI を利用する処理は API 呼び出しに失敗した場合フェイルセーフとしてスコア 0 を返す等の設計になっていますが、API キーと使用料は運用側で管理してください。
- J-Quants の ID トークンは自動リフレッシュ処理が入っています。環境変数にリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を設定してください。
- DuckDB での executemany に空リストを渡すとエラーとなるバージョンがあるため、ETL 実装は空チェック済みです（既に対応済み）。
- run_daily_etl 等は副作用（ネットワーク/DB 書き込み）を伴うため、テスト時はモック（unittest.mock）で外部依存を差し替えてください。コード中に差し替えポイントが用意されています（例: _call_openai_api の patch）。

---

## 貢献 / 拡張

- 新しいデータソース追加（RSS ソース追加、J-Quants 以外の API）
- 取引実行部分（kabuステーション連携）の実装拡張
- 研究用指標・アルゴリズムの追加（feature_exploration / factor_research の拡張）
- モニタリング / アラート（Slack 連携）の追加

README にない詳細な利用方法や API の仕様は各モジュールの docstring を参照してください。質問や補足が必要であれば教えてください。