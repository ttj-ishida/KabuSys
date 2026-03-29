# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集・NLP（LLM）評価、ファクター計算、監査ログ（トレーサビリティ）などを含むデータ基盤と研究ツール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（関数内部で datetime.today()/date.today() を直接参照しない等）
- DuckDB をメインの分析ストアとして利用
- API 呼び出しはレート制御・リトライを実装（J-Quants / OpenAI 等）
- 冪等性・トランザクション考慮（DB 書き込みは ON CONFLICT / BEGIN/COMMIT を利用）
- テスト容易性を考慮して API キー注入やモック差替えが可能

---

## 機能一覧

- データ ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場情報、マーケットカレンダーの差分取得／保存（pagination・再取得・バックフィル対応）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、主キー重複、日付整合性チェック（market_calendar と照合）
  - run_all_checks でまとめて実行
- ニュース収集
  - RSS フィード取得、前処理、ID 正規化（URL トラッキング除去）、raw_news への冪等保存、news_symbols で銘柄紐付け
  - SSRF/サイズ/Gzip/XML 脆弱性対策を実装
- ニュース NLP（LLM）
  - 銘柄別に記事を集約して OpenAI（gpt-4o-mini）に送信し ai_scores テーブルへ保存（score_news）
  - 再試行・レスポンスバリデーション・スコアクリップを実施
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を daily 判定
- 研究（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）
  - settings オブジェクトで各種設定にアクセス可能

---

## 前提 / 要件

- Python 3.9 以上（型アノテーションに合わせて適宜）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード 等）

（実際の requirements.txt はプロジェクトに合わせて作成してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   - 例（requirements.txt がある場合）:
     ```bash
     pip install -r requirements.txt
     ```
   - 最小例:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. パッケージを編集可能モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

   必須環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知に必要（本プロジェクトの Slack 統合を使う場合）
   - SLACK_CHANNEL_ID: Slack 投稿先チャンネル
   - KABU_API_PASSWORD: kabu API（kabuステーション）パスワード
   - OPENAI_API_KEY: OpenAI を利用する場合（score_news/score_regime に環境変数が無い場合は api_key 引数で注入可能）
   - （任意）DUCKDB_PATH / SQLITE_PATH を指定してデータベースファイルパスを変更可能

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxx
   SLACK_BOT_TOKEN=xoxb-xxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（クイックスタート）

以下はライブラリをインポートして各機能を呼ぶ最小例です。実運用時はログ設定やエラーハンドリングを追加してください。

- DuckDB 接続準備（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの LLM スコア付け（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数で設定しておくか、api_key を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB 初期化（監査専用 DB を別ファイルで用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit に対して監査ログの INSERT 等を実行できます
  ```

- ファクター計算（research）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records: list[dict] (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意: OpenAI 呼び出しはネットワーク・課金が発生します。テスト時はモジュール内部の _call_openai_api をモックすることが推奨されています。

---

## 主要な設定・挙動メモ

- 自動 .env 読み込み
  - プロジェクトルートはこのモジュールの __file__ を基点に親ディレクトリを探索し、.git または pyproject.toml が見つかればそこをプロジェクトルートとみなします。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI API
  - 各 AI モジュールは api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
  - LLM のレスポンスは厳密 JSON を期待しますが、冗長なテキストへの耐性やパース回避策も実装されています。

- J-Quants API
  - get_id_token は JQUANTS_REFRESH_TOKEN を使用して id token を取得します（自動リフレッシュあり）
  - レートリミット/リトライ/バックオフが内蔵されています

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                          # 環境変数 / settings 管理
    - ai/
      - __init__.py
      - news_nlp.py                      # ニュース NLP / score_news
      - regime_detector.py               # レジーム判定 / score_regime
    - data/
      - __init__.py
      - jquants_client.py                # J-Quants API クライアント + 保存処理
      - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
      - etl.py                           # ETLResult のエクスポート
      - news_collector.py                # RSS 収集
      - calendar_management.py           # 市場カレンダー管理
      - stats.py                         # 統計ユーティリティ（zscore_normalize）
      - quality.py                       # データ品質チェック
      - audit.py                         # 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py               # ファクター計算（momentum/value/volatility）
      - feature_exploration.py           # 将来リターン / IC / summary
    - research/（その他）
    - (strategy/, execution/, monitoring/ 等は __all__ に含まれるが本サンプルでは省略)

---

## 開発者向け注意点

- DuckDB バージョン依存や executemany の挙動に注意（コメントに記載）。
- テストでは外部 API を実際に叩かず、API 呼び出し部分をモックすること。
- LLM の呼び出しはレスポンスの形式に依存するため、プロンプトや JSON モードの挙動に注意。
- production 環境での live 発注を行うモジュールを用いる場合は十分な安全確認（ペーパー取引での検証・ログ監査）を必須とする。

---

## ライセンス / 貢献

README に含まれるコードの利用や貢献方針はリポジトリの LICENSE を参照してください。

---

必要であれば README に追加したい具体的な例（.env.example の完全版、requirements.txt の中身、CI 実行手順、ユニットテスト実行方法等）を教えてください。