# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと自動売買リサーチ基盤を目的としたライブラリです。J-Quants / RSS / OpenAI（LLM）などからデータを取得・加工し、DuckDB に保存、ファクター計算・品質チェック・ニュース NLP・市場レジーム判定などを行うモジュール群を提供します。

主な用途:
- 日次 ETL（株価・財務・マーケットカレンダー）の自動化
- ニュースの収集と LLM による銘柄センチメント付与
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究（ファクター計算、将来リターン、IC 計算）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

---

## 機能一覧

- 設定管理
  - .env / 環境変数からの設定読み込み（自動ロード、無効化フラグあり）
  - 設定値のバリデーション（環境・ログレベルなど）
- データ取得 / ETL
  - J-Quants API クライアント（差分取得、ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - ETL パイプライン（market_calendar / daily_prices / financials の差分取得・保存）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合検出
  - QualityIssue オブジェクトで問題を集約
- ニュース収集 / NLP
  - RSS から記事収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（ai_scores テーブルへ保存）
  - マクロニュースを用いた市場レジーム判定（1321 ETF の MA200 乖離 + LLM のセンチメント合成）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化関数（init_audit_db）

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトに合わせて追加依存を requirements.txt にまとめてください。

---

## セットアップ手順

1. リポジトリをクローンして venv を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実運用では requirements.txt を用意して `pip install -r requirements.txt` を使ってください。

3. 環境変数 / .env を準備
   プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視等）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）

   .env 例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-....
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. データベースや監査テーブルの初期化（必要に応じて）
   監査ログ DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 返された conn で他の監査操作が可能
   ```

---

## 使い方（主要 API 例）

以下は主要ユーティリティの簡単な利用例です。実運用ではログ設定やエラーハンドリングを適切に追加してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from pathlib import Path

  db_path = Path("data/kabusys.duckdb")
  db_path.parent.mkdir(parents=True, exist_ok=True)
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {written} scores")
  ```

- 市場レジームの判定（market_regime テーブル更新）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 返り値は各銘柄ごとの dict のリスト
  ```

- 監査 DB 初期化（in-memory も可）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db(":memory:")
  # 監査テーブルが作成される
  ```

---

## 環境変数自動ロード挙動

- パッケージ import 時に、プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を順に読み込みます。
  - 読み込み優先順位: OS 環境 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成

主要なファイルとモジュール（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（銘柄スコアリング）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアントと保存処理
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理／営業日判定
    - news_collector.py     — RSS ニュース収集
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / summary
  - research/*            — 研究用ユーティリティ群
  - その他: strategy/, execution/, monitoring/（パッケージ出口として __all__ に定義あり）

（上記は現行コードベースの主なモジュール構成です。実際のリポジトリでは更にユーティリティや CLI、テストが存在する可能性があります。）

---

## 注意点 / 運用上のヒント

- Look-ahead bias（未来情報の参照）を避ける設計が随所に組み込まれています。API 呼び出しや日付操作で date.today() / datetime.today() を直接参照しないよう実装されています。バックテスト時は target_date を明示してください。
- OpenAI 呼び出しには API キーが必要です。キーは関数に引数で注入可能（テストで差し替えやモックがしやすい設計）。
- J-Quants API のレート制限や 401 自動リフレッシュ、ページネーション処理は jquants_client に実装済みです。運用時の例外・ログは必ず確認してください。
- DuckDB の executemany に関する注意（空リスト渡し不可）やトランザクションの扱い（init_audit_schema の transactional オプション）に留意してください。
- RSS 取得は SSRF 対策や受信サイズ上限、XML の安全パーサ（defusedxml）を使用していますが、実運用ではソースの信頼性を確認してください。

---

必要であれば README に以下を追加できます:
- requirements.txt の推奨内容
- 実験用スクリプト / cron / Airflow などのジョブ例
- DB スキーマ定義の詳細ドキュメント
- テスト実行方法

追加の要望（英訳、詳しいセットアップ手順、CI/CD 連携例など）があれば教えてください。