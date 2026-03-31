# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。  
データ取得（J-Quants）／ETL、ニュースからの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。バックテストや運用バッチの基盤として使えるモジュール群を含みます。

---

## 機能一覧

- 環境設定管理
  - .env ファイルや環境変数から設定を自動読込（自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 必須設定の取得とバリデーション（settings オブジェクト）

- データ取得・ETL（jquants_client / pipeline）
  - J-Quants API から株価日足、財務データ、JPX カレンダー等を取得（ページネーション対応）
  - レートリミット／リトライ／トークン自動更新対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
  - QualityIssue で問題を集約

- カレンダー管理（data.calendar_management）
  - 営業日の判定・前後営業日の取得・期間内営業日列挙
  - JPX カレンダー更新ジョブ（calendar_update_job）

- ニュース収集（data.news_collector）
  - RSS 取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（冪等）

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出
  - チャンク／バッチ処理、リトライ、レスポンスバリデーション、ai_scores への保存

- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを組み合わせて日次レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライやフォールバックを実装

- 研究・特徴量（research）
  - momentum, value, volatility などのファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリ等
  - zscore_normalize 等の統計ユーティリティ

- 監査ログ（data.audit）
  - signal → order_request → execution の監査テーブル定義と初期化（DuckDB）
  - 監査DB 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 要求環境 & 依存パッケージ

- Python 3.10+
- 推奨主要依存（例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt を用意してください。最低限の例:

pip install duckdb openai defusedxml

（環境によっては追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # または requirements.txt があれば:
   # pip install -r requirements.txt
   ```

4. 環境変数 / .env の設定
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます。
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   重要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
   - DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
   - SQLITE_PATH (任意): 監視用 SQLite データベースパス

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxx"
   OPENAI_API_KEY="sk-xxxxx"
   KABU_API_PASSWORD="passwd"
   SLACK_BOT_TOKEN="xoxb-xxxxx"
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB 初期化（監査用の例）
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)  # ファイルを作成してスキーマを初期化
   ```

---

## 使い方（主要な例）

- DuckDB 接続の取得（設定に従う）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコア（1日分）を作成して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ保存）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- カレンダー・営業日判定
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 監査ログ用 DB 初期化（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

注意:
- OpenAI の呼び出しは api_key 引数で上書きできます（例: score_news(..., api_key="sk-...")）。未指定時は環境変数 OPENAI_API_KEY を使用します。
- ETL / ニュース収集 / LLM 呼び出しはネットワーク／API の呼び出しを伴うため、実運用では適切なエラーハンドリングとレート管理を行ってください。

---

## ディレクトリ構成（抜粋）

src/kabusys
- __init__.py — パッケージ初期化、version
- config.py — 環境変数・設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores への書込）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理
  - etl.py — ETL インターフェース（ETLResult の公開）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（QualityIssue 等）
  - audit.py — 監査ログスキーマ初期化・DB 作成
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 取得・前処理・保存ロジック
- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- research/*（他ユーティリティ）
- （そのほか）strategy, execution, monitoring モジュールが __all__ に含まれる設計（実装は別ファイル/将来追加）

---

## 実運用上の注意点

- 環境変数や API キーは機密情報です。公開リポジトリに置かないでください。
- LLM/API 呼び出しはコストがかかるため、バッチやキャッシュ戦略を検討してください。
- .env の自動読込はプロジェクトルート（.git または pyproject.toml を基準）を探索します。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に制御できます。
- DuckDB のバージョン差により executemany の挙動（空リスト）に差異があるため、モジュール内で対応しています。ライブラリのバージョンを固定して運用してください。

---

この README はコードベースからの抜粋を元に作成しています。追加の利用例・運用手順・CI 設定などはプロジェクトの運用ポリシーに応じて追記してください。必要であれば README を英語化したり、使用例スクリプトを用意します。