# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株のデータ収集・品質管理・リサーチ・AIによるニュースセンチメント評価・監査ログ・ETL パイプラインを提供する Python ライブラリです。J-Quants API、DuckDB、OpenAI（LLM）などと連携し、バックテスト／運用環境で使用できるデータ基盤および研究ツール群を含みます。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants からの株価（日足）、財務、JPX マーケットカレンダー取得（ページネーション・レート制御・リトライ付き）
  - 差分更新・バックフィル、DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損値・主キー重複・将来日付・スパイク検出などの品質チェック（quality.run_all_checks）
- ニュース収集・NLP（AI）
  - RSS からのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI を使った銘柄ごとのニュースセンチメント算出（news_nlp.score_news）
  - マクロニュースと ETF MA200乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
- リサーチ支援
  - Momentum / Volatility / Value 等のファクター計算（research.calc_*）
  - 将来リターン・IC（Information Coefficient）・統計サマリー・Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマと初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（優先順位あり）と Settings API（kabusys.config.settings）

---

## 要件（例）

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

2. 仮想環境作成・依存パッケージをインストール（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env ファイル
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと、自動でロードされます。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（少なくとも運用する機能に応じて設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注系）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
     - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（省略時 "development"）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（省略時 "INFO"）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB ファイルの配置
   - settings.duckdb_path で指定したパス（デフォルト data/kabusys.duckdb）が利用されます。初回はスキーマ作成ユーティリティを実行してください（プロジェクトにスキーマ初期化用の関数があればそちらを使用）。

---

## 使い方（代表的なコード例）

以下は最小限の利用例です。適切なエラーハンドリング・ロギングを追加して使ってください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
  print("written:", n_written)
  ```

- 市場レジームを評価する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を利用
  ```

- 監査ログ用の専用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026, 3, 20))
  print(len(recs))
  ```

注意:
- AI モジュール（news_nlp/regime_detector）は OpenAI の Chat Completions（gpt-4o-mini）を想定しています。API キーと必要ライブラリを事前に準備してください。
- J-Quants クライアント（data.jquants_client）は API レート制御とリトライを内蔵しています。JQUANTS_REFRESH_TOKEN を設定してください。

---

## 環境変数・設定の詳細

- 自動ロード順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings API:
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.slack_bot_token, settings.slack_channel_id
  - settings.duckdb_path (Path)
  - settings.sqlite_path (Path)
  - settings.env, settings.log_level, settings.is_live, settings.is_paper, settings.is_dev

設定が必須で未設定の場合、Settings のプロパティは ValueError を投げます（必須キーは _require 関数でチェック）。

---

## ディレクトリ構成

（抜粋 / 主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）と関連ユーティリティ
    - regime_detector.py     — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           — ETL パイプラインと run_daily_etl
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 収集（SSRF対策・正規化等）
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - audit.py              — 監査ログスキーマ初期化（signal/order/execution）
    - quality.py            — データ品質チェック
    - stats.py              — 共通統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー 等
  - research/（その他ファイル）
  - その他: strategy/, execution/, monitoring/（パッケージ公開用プレースホルダ）

---

## 実運用上の注意点

- Look-ahead bias 対策: 多くの関数は date や DB データに対して「target_date 未満/以前」等の条件を厳格に扱うことで将来情報の混入を避ける設計になっています。バックテストや研究で使用する際は target_date を明示してください。
- OpenAI 呼び出し: 429/ネットワーク断/タイムアウト/5xx に対するリトライとフェイルセーフ（失敗時はスコア 0.0 を採用）を実装していますが、APIコスト・レートに注意してください。
- J-Quants: レート制限（120 req/min）や 401 自動リフレッシュを考慮しています。refresh token の管理に注意してください。
- DuckDB バージョン依存: コード中に DuckDB のバージョン特性を考慮した処理（executemany の空リスト制約 等）があります。使用する DuckDB バージョンと互換性を確認してください。

---

## 開発・テスト

- 環境変数自動ロードをテストで抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI / ネットワーク呼び出しは外部 API に依存するため、ユニットテストでは該当関数（_call_openai_api や _urlopen 等）をモックすることを推奨します（コード中にも patch 用の注釈あり）。

---

README に含めた情報はコードベースの概要・代表的な使い方に基づく要約です。より詳細な API の使い方やスキーマ定義、運用手順はプロジェクト内の設計ドキュメント（DataPlatform.md / StrategyModel.md 等）やソースコードの docstring を参照してください。必要であれば README に追加するサンプルコマンドや図、運用手順（cron / Airflow 例）も記載できます。