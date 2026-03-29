# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、AI を使った市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

## 主な特徴
- データ取得（J-Quants API）と DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（市場カレンダー・株価・財務データ、品質チェック）
- ニュース収集（RSS）と LLM による銘柄別ニュースセンチメント（gpt-4o-mini / JSON mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）および特徴量解析ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化
- 環境変数 / .env による設定管理（自動読み込み、プロジェクトルート探索）

---

## 機能一覧（モジュール概観）
- kabusys.config
  - 環境変数と .env の自動読み込み、必須値チェック（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、取得、DuckDB 保存関数）
  - pipeline / etl: 日次 ETL 実行関数（run_daily_etl など）と ETL 結果型
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS 取得・正規化・保存ロジック（SSRF 対策、サイズ制限）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブル DDL と初期化ヘルパー（init_audit_db / init_audit_schema）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores テーブルに書込
  - regime_detector.score_regime: MA200 とマクロニュースで日次市場レジームを判定して market_regime に書込
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件
- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI を使用する場合）

依存パッケージはプロジェクト側の requirements.txt / pyproject.toml に合わせてインストールしてください。

---

## インストール（開発用）
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. パッケージをインストール（プロジェクトルートで）:
   - pip install -e .    （セットアップがある場合）
   - または必要なライブラリを個別に pip install duckdb openai defusedxml

---

## 環境変数 / 設定
自動的にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます（環境変数の優先度: OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知等）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト INFO）

設定値は `from kabusys.config import settings` で参照できます（例: settings.jquants_refresh_token）。

---

## セットアップ手順（最小）
1. 必須環境変数を設定（.env を作成）:
   - .env 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXX
     KABU_API_PASSWORD=your_password

2. DuckDB データベースを用意（デフォルトは data/kabusys.duckdb）:
   - Python から:
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     # 必要なスキーマは ETL/スキーマ初期化関数で作成する（プロジェクトにスキーマ init モジュールがある想定）

3. 監査ログ専用 DB を初期化する（任意）:
   - from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 基本的な使い方（コード例）
以下は主要ユースケースの簡単なサンプルです。各関数は DuckDB 接続と target_date（date オブジェクト）を受け取ります。

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（ai_scores テーブルへ書込）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定
  cnt = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("scored:", cnt)
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算（研究用途）:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  ```

- 将来リターンや IC, 統計サマリー:
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 監査ログスキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

---

## 実運用上の注意 / 設計上のポイント
- AI 呼び出し（OpenAI）は各関数でリトライやフェイルセーフを備えていますが、APIキーの制御やコスト管理はユーザー側で行ってください。
- AI 関連関数は api_key 引数を受け取るため、テスト時はモック注入が可能です（ユニットテストでの差替えを推奨）。
- ETL やデータ取得では Look-ahead バイアス対策が各所で設計されています（target_date 未満のみ参照、fetched_at 記録等）。
- news_collector は SSRF / XML Bomb / 大容量レスポンス対策を実装しています。RSS URL は必ず http/https を使用してください。
- .env の自動読み込みはプロジェクトルート探索に基づきます。CIやテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

## ディレクトリ構成（主要ファイル）
（src 配下の主要モジュール。実際のプロジェクトでは tests/、scripts/ 等もある想定）

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
    - etl.py (ETLResult 再エクスポート)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema init 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは data.stats を再利用してファクター計算を行います。

---

## テスト / 開発のヒント
- OpenAI 呼び出しやネットワーク I/O はユニットテストでモックしやすいように設計されています。例:
  - unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
  - unittest.mock.patch("kabusys.ai.regime_detector._call_openai_api")
  - news_collector の _urlopen を差し替えてネットワーク依存を切る
- 自動 .env ロードはテストで副作用を起こす可能性があるため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

---

必要に応じて README に具体的な導入スクリプトや schema 初期化サンプル、CI 用のセットアップ手順を追加できます。ほかに記載したい使用例や環境（Docker / systemd / cron での運用例など）があれば教えてください。