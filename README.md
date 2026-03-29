# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質検査、ニュース収集とAIによるニュースセンチメント評価、調査／ファクター計算、監査ログ（トレーサビリティ）などを含むコンポーネント群を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ収集 / ETL
  - J-Quants API を使った株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- データ品質管理
  - 欠損、重複、日付不整合、スパイク検出などの品質チェック
- ニュース収集
  - RSS フィードからの安全なニュース収集（SSRF対策、サイズ制限、ID生成・正規化）
  - 銘柄との紐付け（news_symbols / raw_news）
- AI モジュール
  - ニュースの銘柄別センチメントスコア化（OpenAI gpt-4o-mini を想定、JSON mode を利用）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを組み合わせる）
  - バッチ・リトライ・レスポンス検証を備えた堅牢な実装
- 研究用ユーティリティ
  - ファクター（Momentum / Value / Volatility 等）計算、将来リターン、IC 計算、Z スコア正規化など
- 監査ログ（audit）
  - signal → order_request → execution まで追跡できる監査スキーマと初期化ユーティリティ
- 設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）と環境変数ラッパー（settings）

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（主な依存）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／展開して、プロジェクトルートへ移動します（.git または pyproject.toml をルート検出に使用します）。

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存ライブラリをインストール
   - 例（最小）:
     - pip install duckdb openai defusedxml

   - またはプロジェクトに requirements.txt / pyproject があればそれに従ってください:
     - pip install -r requirements.txt
     - または pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト、自動ロード有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

   代表的な変数（README 用サンプル）:
   - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C0123456
   - OPENAI_API_KEY=sk-...
   - KABUSYS_ENV=development  # development / paper_trading / live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API と実行例）

以下はライブラリ内の主要機能を実行するための最小例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

- ETL（デイリー ETL 実行）
  - 実行例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースセンチメント（銘柄ごとの AI スコア）
  - 実行例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print("scored_count:", count)
    ```

- 市場レジーム判定
  - 実行例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    ```

- 監査ログ DB の初期化
  - 実行例:
    ```python
    from kabusys.data.audit import init_audit_db

    conn = init_audit_db("data/audit_duckdb.db")
    # conn は DuckDB 接続（監査テーブルが作成済み）
    ```

- 設定参照
  - 実行例:
    ```python
    from kabusys.config import settings

    print(settings.jquants_refresh_token)
    print(settings.duckdb_path)
    print(settings.env, settings.log_level)
    ```

注記:
- AI モジュールは OpenAI の API（gpt-4o-mini を想定）を使用します。APIキーは `OPENAI_API_KEY` 環境変数、または各関数の `api_key` 引数で指定してください。
- J-Quants API 利用時は `JQUANTS_REFRESH_TOKEN` が必要です。jquants_client はトークンを自動でリフレッシュします。
- run_daily_etl などの処理は副作用（DB 書き込み）を伴います。実行前に DB のバックアップやテスト環境での検証を推奨します。

---

## .env 自動読み込みの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml のいずれかがある親ディレクトリ）を探索し、見つかった場合はそのルート下の `.env` と `.env.local` を読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` 上書き用（override=True）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で使用）。

---

## 注意点 / 設計ポリシー（運用上のポイント）

- Look-ahead バイアス防止
  - AI モジュール・ETL・研究モジュールは内部で datetime.today()/date.today() をむやみに参照せず、明示的な target_date を受け取る設計になっています。バックテストや検証での時間整合性に配慮しています。
- フェイルセーフ
  - AI API・外部 API の失敗時は例外で即中断せず、フォールバック（例: macro_sentiment=0.0）で処理継続する箇所があります。ログで失敗状況を追跡してください。
- 冪等性
  - J-Quants データ保存やニュース保存、監査スキーマ初期化などは冪等操作（ON CONFLICT や一意制約）を想定しています。
- レート制御
  - jquants_client は J-Quants のレート（120 req/min）を守るための簡易 RateLimiter を備えています。

---

## ディレクトリ構成（主なファイル・モジュール）

（パスは src/kabusys 以下を示します）

- __init__.py
- config.py — 環境変数 / 設定ラッパー（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント計算（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL API の再エクスポート
  - news_collector.py — RSS ニュース収集
  - calendar_management.py — マーケットカレンダー管理・営業日判定
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログ定義・初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring, strategy, execution, etc.
  - パッケージ全体のエントリや上位モジュール（README の冒頭で __all__ に挙げられているモジュール群を参照）

（実際のトップレベル構成はリポジトリルートの構成に依存します）

---

## よく使う参考スニペット

- DuckDB 接続の例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- AI 関連の例（環境変数から API キーを使う場合は api_key 引数を省略可）:
  ```python
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=date(2026,3,20))
  ```

---

## トラブルシューティング

- 環境変数が見つからないエラー:
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）は未設定だと ValueError を送出します。`.env` を作成するか環境変数を設定してください。
- OpenAI / J-Quants 呼び出しの認証エラー:
  - トークンの有効性を確認し、jquants_client の場合は refresh token が正しく設定されていることを確認してください。
- 大量データや API レートによる問題:
  - jquants_client は内部でスロットリングとリトライを行いますが、運用時は取得間隔や並列実行数に注意してください。

---

必要であれば、各モジュール（ETL・AI・news_collector・jquants_client 等）の使い方サンプルや初期スキーマ（DuckDB のテーブル定義）を追加で記述します。どの部分の詳しいドキュメントが欲しいか教えてください。