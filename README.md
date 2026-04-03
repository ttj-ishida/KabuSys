# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL、ニュース収集、データ品質チェック、ファクター計算、AI（ニュースNLP / 市場レジーム判定）、監査ログ、J-Quants クライアント等を含むモジュール群を提供します。

主にバックテスト / リサーチ / 運用のための共通ユーティリティ群として設計されています。ルックアヘッドバイアス防止や冪等性（idempotency）、外部APIの堅牢な呼び出し・リトライ等に配慮しています。

---

## 主な機能（概要）

- データ取得・ETL
  - J-Quants API クライアント（株価日足・財務・カレンダー等の取得、保存）
  - 差分ETL / 日次ETL パイプライン（run_daily_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理
  - RSS 収集器（SSRF・サイズ制限・トラッキング除去等の堅牢化）
  - ニュース → 銘柄マッピング（news_symbols 参照）
- AI（OpenAI）
  - ニュースセンチメント（ニュースを銘柄ごとにまとめて LLM でスコア化: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成: score_regime）
  - OpenAI への呼び出しは JSON mode を利用、リトライ/フォールバック実装あり
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC 計算、ファクター統計サマリー、Z スコア正規化ユーティリティ
- 監査ログ（オーディット）
  - signal_events / order_requests / executions などの監査テーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- カレンダー管理
  - JPX カレンダーの更新・営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
- 設定管理
  - .env 読み込み（プロジェクトルート基準）、環境変数経由の設定アクセス（kabusys.config.settings）

---

## 前提・必須ソフトウェア

- Python 3.10+
- 推奨（pip パッケージ）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt に依存関係をまとめてください。ここではコードから必要な主なパッケージを挙げています。）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージをインストール
   - (開発) editable インストール:
     ```
     git clone <repo>
     cd <repo>
     pip install -e .
     ```
   - もしくは requirements に記載の依存をインストール:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数の設定
   - プロジェクトルートの `.env` または OS 環境変数で設定します。自動ロードはデフォルトで有効（`.git` または `pyproject.toml` を上位に探索して `.env`/.env.local を読み込み）。
   - 自動ロード無効化:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に必要）
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）

   - .env のサンプル:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     ```

3. DuckDB の初期化（監査ログなど）
   - 監査DBを初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     from pathlib import Path

     db_path = Path("data/kabusys_audit.duckdb")
     conn = init_audit_db(db_path)  # テーブルとインデックスを作成
     conn.close()
     ```
   - 既存の DuckDB 接続にスキーマだけ適用する:
     ```python
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 基本的な使い方（例）

- ETL（日次パイプライン）の実行例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメント（ai.news_nlp.score_news）の実行例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  conn.close()
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）の実行例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  conn.close()
  ```

- ファクター計算（research）例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  conn.close()
  ```

- カレンダー関連ユーティリティ例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  conn.close()
  ```

注意:
- score_news / score_regime は OpenAI API キーが必要です（api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください）。API 呼び出し失敗時はフェイルセーフとして 0 を返す挙動がありますが、キー未設定の場合は ValueError を送出します。
- J-Quants 関連のデータ取得は JQUANTS_REFRESH_TOKEN が必須です。get_id_token / fetch_* で利用されます。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI の API キー（AI スコアリングに必要）
- KABU_API_PASSWORD: kabu API 用パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に 1 を設定

---

## トラブルシューティング

- ValueError: "環境変数 'X' が設定されていません"  
  → 必須の環境変数を設定してください（JQUANTS_REFRESH_TOKEN や OPENAI_API_KEY 等）。

- OpenAI / J-Quants の API 呼び出し失敗（RateLimitError / Network 等）  
  → ライブラリ内でリトライ実装がありますが、API キーやネットワーク、レート制限状況を確認してください。

- DuckDB に関するエラー  
  → schema が未作成の場合は init_audit_schema / init_audit_db 等でスキーマを初期化してください。ETL 実行前に必要テーブルの存在を確認してください。

---

## ディレクトリ構成

（主なファイル / モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py           — ニュース NLP（score_news）
      - regime_detector.py    — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント / 保存ロジック
      - pipeline.py           — ETL パイプライン（run_daily_etl 等）
      - etl.py                — ETLResult 再エクスポート
      - news_collector.py     — RSS ニュース収集
      - calendar_management.py— 市場カレンダー管理
      - quality.py            — データ品質チェック
      - audit.py              — 監査ログ（スキーマ初期化）
      - stats.py              — 汎用統計ユーティリティ
    - research/
      - __init__.py
      - factor_research.py    — ファクター計算（momentum/value/volatility）
      - feature_exploration.py— 特徴量探索（IC / forward returns / summary）
    - (strategy/, execution/, monitoring/ 等のパッケージが想定されるがここでは省略)

---

## 開発上の設計方針（要点）

- ルックアヘッドバイアス防止: 内部処理は明示的に target_date を受け取り、date.today() を直接参照しない箇所を基本としています（ETL の外側で基準日を制御可能）。
- 冪等性: DB 保存は ON CONFLICT / DELETE→INSERT のパターンで上書き可能にし、再処理を安全にしています。
- フェイルセーフ: 外部API失敗時は全停止させず、影響範囲を限定して継続するよう設計（ログ・警告を残す）。
- テスト容易性: API 呼び出し等は内部関数の差し替え（mock）ができるよう実装されています。

---

## 貢献 / 追加実装の案内

- strategy / execution / monitoring モジュールの統合（実運用での注文送信 / リスク管理 / プロセス監視）
- CI / テストケース（モックを利用したユニットテスト）
- requirements.txt / pyproject.toml の整備、Docker 化
- 運用向けのログ出力・メトリクス、LINE 通知等の実装拡張

---

必要に応じて README にサンプル .env.example、詳しい CLI/サービスの起動手順、Dockerfile、依存関係リストを追加できます。どの情報を優先的に追記したいか教えてください。