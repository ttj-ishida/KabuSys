# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ収集（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（約定トレーサビリティ）など、ストラテジー開発／リサーチから実運用に必要なコンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能群を備えたモジュール群です。

- J-Quants API を使った株価／財務／カレンダーの差分取得・保存（DuckDB）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境変数ベースの Settings）

設計上の注意点：
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を直接参照しない関数設計）
- API 呼び出しはリトライ・バックオフ・レート制御を備える
- DuckDB をデータストアとして使用（ローカル・軽量で高速な分析向け）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存関数）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得、前処理、DB 保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: 市場レジーム判定と market_regime への書き込み
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数の自動読み込み（.env, .env.local）および Settings オブジェクト

---

## 必要条件

- Python 3.10 以上（| 型注釈や新しい型構文を使用）
- 推奨パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, 各 RSS, OpenAI）

（プロジェクトに requirements.txt がある場合はそちらを使用してください。無ければ上記パッケージを手動でインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env または環境変数から設定を読み込みます。パッケージはインポート時にプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索し、`.env` → `.env.local` の順に自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使われる環境変数（Settings 参照）：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベースURL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite (monitoring 用) のパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY — OpenAI API キー（ai.score の呼び出しでは引数で上書き可）

.env.example を用意して .env を作成することを推奨します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # 追加で requests 等を使う箇所があれば適宜インストール
   ```

4. .env を作成し必須環境変数を設定
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など

5. DuckDB データベースの準備（監査用 DB を初期化する例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # または既存の conn に init_audit_schema を適用
   ```

6. ETL を実行してデータを取得
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

---

## 使い方（主要な例）

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントスコア生成（銘柄別 ai_scores へ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

  api_key を省略すると環境変数 `OPENAI_API_KEY` が使用されます。

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（例: momentum）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルとインデックスが作成されます
  ```

---

## 運用上のポイント・注意事項

- J-Quants API はレート制限（120 req/min）に配慮した実装が組み込まれています。大量取得の際はパラメータや間隔を調整してください。
- OpenAI 呼び出しはコストとレイテンシが発生します。バッチサイズやリトライ設定はコード内定数で調整可能です（news_nlp/_BATCH_SIZE 等）。
- 自動.env 読み込みはインポート時に実行されます。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルは適切にバックアップしてください。監査ログは削除しない運用が想定されています。
- ニュース収集においては SSRF 防御や受信サイズ上限、XML パースの防御（defusedxml）を実装していますが、追加のセキュリティ対策は運用環境に応じて行ってください。

---

## ディレクトリ構成（主要ファイル）

（実際のツリーはリポジトリのルートを基準にしてください。以下は src/kabusys 以下の主なファイル一覧）

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
    - stats.py
    - quality.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート用)
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（ユーティリティを再エクスポート）
  - ai/（LLM 関連）
  - data/（ETL・DB・ニュース・品質・監査）
  - research/（ファクター・解析）

---

## 追加情報 / 開発者向け

- テスト: LLM / 外部 API を呼ぶ箇所はモック可能な設計になっています（_call_openai_api 等を patch してテスト）。
- トランザクション: ETL・監査スキーマ初期化など一部は BEGIN/COMMIT/ROLLBACK を使って冪等性を担保しています。DuckDB の executemany における空リスト挙動など実行環境依存の注意があります。
- ロギング: モジュールごとに logger を利用しています。LOG_LEVEL を設定してログ出力を制御してください。

---

もし README に追加したいスクリーンショット、サンプル .env.example、requirements.txt、あるいは具体的な実行スクリプト（CLI）などがあれば提供してください。README をそれに合わせて拡張します。