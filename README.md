# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS / OpenAI を利用したデータ収集・品質チェック・ニュースNLP・市場レジーム判定・ファクタ研究・監査ログ機能などをまとめたモジュール群です。

> 注: これはライブラリ / バッチ処理向けの内部実装を想定したコードベースの README です。実運用では各種 API キー・証券会社接続情報・リスク管理ルールを適切に設定してください。

---

## 主な特徴（機能一覧）

- ETL（jquants → DuckDB）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（冪等）
  - バックフィル / ページネーション / レート制御 / リトライ
- データ品質チェック
  - 欠損・重複・将来日付・前日比スパイク検出（QualityIssue を返却）
- ニュース収集
  - RSS フィード収集、安全対策（SSRF・サイズ制限・トラッキング除去）付き
- ニュース NLP / スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント付与（ai_scores テーブル）
  - バッチ・リトライ・レスポンス検証・スコアクリップ
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成して日次レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に初期化・管理
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須環境変数チェック

---

## 必要条件

- Python 3.10+
  - 型注釈に `|`（PEP 604）を使用しています
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

実際にはプロジェクトの pyproject.toml / requirements.txt に従ってください（この配布には同ファイルが含まれている想定）。

---

## セットアップ手順

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 例（最低限）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用 / テスト用パッケージはプロジェクトの要件に応じて追加してください。
   - プロジェクトを editable install する場合:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（kabusys.config.Settings が要求するもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - OpenAI を使う機能を利用するには:
     - OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector は引数からも渡せます）
   - データベースパス（任意、デフォルト値あり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB。デフォルト: data/monitoring.db）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易サンプル）

以下は Python スクリプトや REPL からの利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB に接続
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（カレンダー取得・価格・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- ニュースセンチメントのスコア（指定日）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数にある場合 api_key は省略可能
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 監査用テーブルが作成されます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- RSS のフェッチ（単体で記事取得）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは API 費用が発生します。API キー・リトライ挙動に注意してください。
- ETL やスコア処理は Look-ahead bias を避ける設計（target_date 未満のデータのみ参照する等）になっています。バッチ処理やバックテストでの使用はこの点に留意してください。

---

## よく使うモジュール説明（抜粋）

- kabusys.config
  - .env 自動読み込み・必須環境変数のチェックを行う Settings
- kabusys.data.jquants_client
  - J-Quants API とやり取りするクライアント（取得・保存関数）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL のエントリ）
- kabusys.data.quality
  - データ品質チェック群（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- kabusys.data.news_collector
  - RSS 取得・前処理・安全対策を持つニュースコレクタ
- kabusys.ai.news_nlp
  - 銘柄別ニュースを LLM でスコア化して ai_scores に書き込む
- kabusys.ai.regime_detector
  - ETF の MA200 乖離とマクロニュース（LLM）から市場レジームを判定
- kabusys.research
  - ファクター計算・IC / 統計サマリー等の研究用ユーティリティ
- kabusys.data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）の初期化・ユーティリティ

---

## 重要な注意点 / 運用上のポイント

- 環境変数や API キーの管理は慎重に（漏洩防止）。
- OpenAI 呼び出しは課金対象です。テスト時はモック化を推奨（モジュール内の `_call_openai_api` は差し替え可能）。
- ETL は外部 API のレート制限やリトライを実装していますが、運用環境のネットワーク事情に応じた監視とアラートを設定してください。
- DuckDB ファイルの取り扱い（バックアップやロック）に注意。複数プロセスでの同時書き込みは設計に依存します。
- 自動 .env ロードはプロジェクトルート検出に基づきます。CI 等で明示的に環境変数を渡す場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（抜粋）:

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
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールはドキュメント（モジュールトップの docstring）と詳細なログ・例外処理を備えています。プロジェクト内部で使用する主要テーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions など）に対応した処理が実装されています。

---

もし README をもっと詳しく（例: 各テーブルのスキーマ、CI 設定例、実運用の監視・再実行ポリシー、テストの実行方法など）に拡張したい場合は、欲しいセクションを教えてください。