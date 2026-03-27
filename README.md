# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（リサーチ・ETL・NLP・監査ログなど）です。  
このリポジトリは、J-Quants / JPX / RSS / OpenAI 等を組み合わせて、データ収集・品質チェック・ファクター計算・AIベースのニュースセンチメント・市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local を自動ロード（プロジェクトルート検出）／無効化フラグあり
- データ収集（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーなどの差分取得・保存（ページネーション・レート制御・自動リフレッシュ）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - run_daily_etl による日次一括処理
- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、SSRF 対策、トラッキングパラメータ除去
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメントスコア化（ai_scores テーブルへ保存）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM スコアを合成して日次レジーム判定（bull/neutral/bear）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC・統計サマリ
- 監査ログ（audit）
  - signal → order_request → execution まで UUID でトレース可能な監査テーブルと初期化ユーティリティ
- 汎用ユーティリティ
  - 統計（Zスコア正規化）やマーケットカレンダー管理など

---

## 動作環境・前提

- Python 3.10 以上（型注釈で union 型 `X | Y` を使用）
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS 取得）
- J-Quants リフレッシュトークン、OpenAI APIキー、kabu API パスワード等の環境変数

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（必要なライブラリを個別にインストール）:
     - pip install duckdb openai defusedxml
   - packaging に応じて requirements.txt / pyproject.toml がある場合はそれに従ってください。
   - 開発中ならパッケージを編集可能モードでインストール:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成します（`.env.example` を参考に作成してください）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の省略時に参照）
     - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb、デフォルト）
     - SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境（development|paper_trading|live）デフォルト development
     - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます（テスト用途）
   - .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）に置くと自動読み込みされます。

---

## 使い方（簡単なコード例）

- 共通: 設定と DuckDB 接続
  ```python
  from kabusys.config import settings
  import duckdb

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API キーは引数または環境変数 OPENAI_API_KEY）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すことも可能
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {written} codes")
  ```

- 市場レジーム算出
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
  ```

- 監査DB初期化（監査専用DBを作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ヘルプ：モジュールの docstring に各関数・引数の説明が豊富に書かれています。IDE や pydoc で参照してください。

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス対策
  - モジュールの多くは datetime.today() / date.today() による参照を避け、関数呼び出し時に対象日を明示的に渡す設計です。
- 冪等性
  - ETL の保存処理（save_*）や監査テーブル初期化は冪等に実行できるよう実装されています（INSERT ... ON CONFLICT）。
- フェイルセーフ
  - OpenAI 呼び出しや外部 API の失敗はソフトに扱い（0.0 をスコアフォールバックする等）、処理全体を止めない作りです。必要に応じて上位で例外を捕捉してください。
- セキュリティ
  - RSS 取得では SSRF 対策、XML の defusedxml 使用、レスポンスサイズ制限等の防御実装があります。
- ロギング
  - 各モジュールで logging を使用。LOG_LEVEL によって出力を調節してください。

---

## 主要なディレクトリ構成（抜粋）

リポジトリ内の主要ファイル群（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境・設定管理（.env ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news）
    - regime_detector.py          — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント + 保存関数
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult 再エクスポート
    - quality.py                  — 品質チェック
    - news_collector.py           — RSS 収集・前処理
    - calendar_management.py      — マーケットカレンダー管理
    - stats.py                    — 統計ユーティリティ（zscore 正規化）
    - audit.py                    — 監査ログ (DDL / init)
  - research/
    - __init__.py
    - factor_research.py          — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py      — 将来リターン・IC・統計サマリ等

（トップレベルには strategy / execution / monitoring パッケージをエクスポートする意図がありますが、実装の追加により拡張されます。）

---

## よくある質問（FAQ）

- Q: OpenAI の呼び出しはどのようにキーを渡すのか？  
  A: score_news / score_regime 等の関数は api_key を引数で受け取れます。None を渡すと環境変数 OPENAI_API_KEY を参照します。

- Q: .env の自動読み込みを無効にしたい。  
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動ロードが無効になります（テスト用途など）。

- Q: DuckDB のデータベース場所を変更するには？  
  A: 環境変数 DUCKDB_PATH を設定してください（Settings.duckdb_path が参照します）。

---

## 貢献 / 開発

- コードの追加やバグ修正は PR を送ってください。  
- 変更時は既存の docstring と設計方針（Look-ahead バイアス防止、冪等性、フェイルセーフ）に沿うよう注意してください。

---

README に記載していない詳細な使い方は各モジュールの docstring を参照してください。質問や追加資料が必要であれば教えてください。