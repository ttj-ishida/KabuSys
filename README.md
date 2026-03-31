# KabuSys

日本株向けのデータプラットフォーム・リサーチ・自動売買に関する共通ライブラリ群です。  
DuckDB をデータ層に持ち、J-Quants / RSS / OpenAI（LLM）など外部サービスと連携して ETL、品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール集合です。

- データ取得・ETL（J-Quants から株価・財務・カレンダーを取得して DuckDB に保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
- ニュース収集・ニュース NLP（RSS からニュースを収集し LLM で銘柄ごとにセンチメントスコア化）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究（ファクター計算、将来リターン・IC・サマリー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティを DuckDB に保存）
- kabu（kabu API）や Slack 通知用の設定管理などのユーティリティ

設計上の特徴：
- Look-ahead bias（将来情報参照）に配慮した実装
- DuckDB を中心に SQL と Python を組み合わせて効率的に処理
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを実装
- 冪等保存（ON CONFLICT / UPDATE）による安全な ETL

---

## 主な機能一覧

- kabusys.config
  - 環境変数・.env 自動読み込み（.env, .env.local）
  - 必須設定の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*, など）

- kabusys.data
  - jquants_client: J-Quants API（取得・保存・認証・ページネーション・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）、個別 ETL（run_prices_etl 等）と ETL 結果型（ETLResult）
  - quality: データ品質チェック（missing / duplicates / spike / date_consistency）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、サイズ制限）
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - audit: 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に渡して銘柄ごとの ai_score を生成し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA + マクロニュース LLM を合成して market_regime に保存

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用した正規化

---

## セットアップ手順

前提: Python 3.10+（typing 機能等を使用しています）。DuckDB を使います。

1. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なライブラリ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` と `.env.local` を配置できます（自動読み込みを行います）。
   - 自動ロードは既定で有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に使用）
   - KABU_API_PASSWORD: kabu API のパスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース（DuckDB）ディレクトリ作成
   - settings.duckdb_path の親ディレクトリを作成しておきます（例: data/）。
   - 多くの初期化関数は接続時に親ディレクトリを自動作成しますが、必要に応じて手動作成してください。

---

## 使い方（代表的な例）

以下はライブラリを使った簡単なコード例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB 接続と日次 ETL の実行（run_daily_etl）:
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（score_news）
  - OpenAI API キーは api_key 引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（score_regime）
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査専用 DB を作る）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

注意点:
- OpenAI の呼び出しはリトライやフェイルセーフを備えていますが、API キー設定が必須です。
- DuckDB のバージョン差異（executemany 空リストの挙動等）に注意して実行してください。

---

## 環境・テストに関するヒント

- .env 自動ロードを無効化してテストしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをテストで置き換える場合:
  - kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch などで差し替え可能です（コード内でそのように設計されています）。
- RSS 取得はネットワーク・SSRF 対策が多数組み込まれているため、テスト時は news_collector._urlopen をモックしてローカルフィードを返すことを推奨します。

---

## ディレクトリ構成（主要ファイル）

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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - (その他: schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research 等のユーティリティは data.stats の関数も利用

各モジュールはドメインごと（data / research / ai / monitoring / execution 等）に分割されており、明確な責務に沿って実装されています。

---

## よくある質問（FAQ）

- Q: .env の読み込みはどのような順番ですか？
  - A: OS 環境変数 > .env.local > .env の順に適用されます。OS 環境変数は protected として上書きされません（.env.local/.env は保護されたキーを上書きしない設定あり）。

- Q: OpenAI キーがないとどうなりますか？
  - A: score_news / score_regime は API キーが必須で、api_key 引数または環境変数 OPENAI_API_KEY を使います。未設定だと ValueError を送出します。

- Q: J-Quants のトークンはどうやって扱うのですか？
  - A: 環境変数 JQUANTS_REFRESH_TOKEN を設定してください。jquants_client.get_id_token がリフレッシュトークンから id_token を取得します。401 を検知した場合は自動的にリフレッシュして再試行する実装があります。

---

フィードバックや改善点があればお知らせください。README に追加したいコマンドやサンプルがあれば追記します。