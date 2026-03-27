# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。J‑Quants / JPX カレンダー / 各種 ETL、ニュースの NLP スコアリング、研究（ファクター計算）、監査ログ表構築などを含むモジュール群を提供します。

主な用途例:
- J-Quants から日次データを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュースの収集と OpenAI による銘柄別センチメントスコア算出
- マーケットレジーム判定（ETF の MA とニュースセンチメントの合成）
- 研究用のファクター計算・特徴量解析ユーティリティ
- 注文／約定などをトレースする監査ログスキーマ初期化

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得ユーティリティ
- データ ETL
  - J-Quants から株価日足、財務データ、カレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - quality モジュールによるデータ品質チェック（欠損、重複、スパイク、日付不整合）
  - ETL の統合エントリ run_daily_etl
- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策、gzip / サイズチェック、トラッキング除去）
  - raw_news / news_symbols を元に銘柄別記事集約
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（score_news）
  - マクロニュースの LLM スコアを用いた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等作成
  - init_audit_db, init_audit_schema による初期化
- J-Quants クライアント
  - 認証（refresh token -> id token）、レートリミッティング、リトライ、保存関数群

---

## セットアップ手順

前提
- Python 3.9+（型ヒント: union 表記等を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS アクセス）
- DuckDB を使用するためのライブラリ（pip インストール対象）

1. リポジトリをチェックアウト（または pip editable install）
   - 開発環境であればプロジェクトルートで:
     ```
     git clone <repo-url>
     cd <repo-dir>
     ```

2. 仮想環境を作成・有効化
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

3. 依存ライブラリをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 一例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETLで必須）
     - KABU_API_PASSWORD : kabuステーション API を使う場合のパスワード
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack 通知先チャンネルID
   - OpenAI を使う場合:
     - OPENAI_API_KEY : score_news / score_regime で使用（関数呼び出し時に api_key を直接渡すことも可能）
   - システム設定:
     - KABUSYS_ENV : development | paper_trading | live （デフォルト development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL

   - 例 `.env`（サンプル、実運用では安全に管理してください）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_pwd
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     ```

5. DuckDB 用データディレクトリ作成
   - 設定でデフォルトは `data/kabusys.duckdb`（settings.duckdb_path）
   - 必要に応じてディレクトリ作成:
     ```
     mkdir -p data
     ```

---

## 使い方（代表的な操作例）

以下は Python スクリプトからライブラリを利用する例です。簡単な説明と共に主要関数の使い方を示します。

1. DuckDB 接続を取得して日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. news_nlp による銘柄センチメントスコア取得（score_news）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   print(f"scored {count} codes")
   ```

3. マーケットレジーム判定（score_regime）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   ```

4. 監査ログ用 DB の初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/monitoring_audit.duckdb")
   # テーブルが作成され、UTC タイムゾーンが設定されます
   ```

5. J-Quants の単独利用例（id_token 取得や一覧取得）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_listed_info

   token = get_id_token()  # .env の JQUANTS_REFRESH_TOKEN を使用
   infos = fetch_listed_info(id_token=token, date_=None)
   ```

注意点:
- OpenAI を利用する処理は API コスト・レート制限に注意してください。
- score_news / score_regime は API 呼び出し失敗時にフェイルセーフ（ゼロスコア等）で処理継続するよう考慮されていますが、キーは必須です（引数または OPENAI_API_KEY 環境変数）。
- ETL は差分更新を行う設計です。初回フルロードやバックフィル時は run_prices_etl 等の date_from を調整してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuAPI 利用時のパスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知のため
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化（テスト用）

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュース NLP スコアリング（score_news）
    - regime_detector.py              -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + 保存関数
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETL の公開インターフェース
    - calendar_management.py          -- マーケットカレンダー管理
    - news_collector.py               -- RSS 収集
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                        -- 監査ログスキーマ定義 & 初期化
  - research/
    - __init__.py
    - factor_research.py              -- Momentum / Value / Volatility ファクター
    - feature_exploration.py          -- 将来リターン / IC / 統計サマリー

その他:
- data/                              -- デフォルトの DB 保存先（DuckDB ファイル等）
- .env, .env.local (任意)            -- 環境変数ファイル（自動読み込み）

---

## 設計上の注意点 / 取り扱い上の注意

- Look-ahead バイアス対策:
  - 各 AI / 指標計算は target_date より未来のデータを参照しないように設計されています（datetime.today() の直接参照回避、DB クエリの排他条件等）。
- 冪等性:
  - J-Quants 保存関数や監査ログ作成は冪等（ON CONFLICT / PRIMARY KEY）を意識して実装されています。
- セキュリティ:
  - RSS 収集は SSRF 対策（スキームチェック、プライベートIPチェック、リダイレクト検査）を実装。
  - API トークンは環境変数で管理し、公開リポジトリに直書きしないでください。
- ロギング・監視:
  - 各処理は logger を利用しており、LOG_LEVEL の設定で出力制御が可能です。
- テスト:
  - 一部の外部 API 呼び出しはユニットテストで差し替え可能（関数単位でモックしやすい設計）。

---

## 開発 / 貢献

バグ修正・機能追加は Pull Request を歓迎します。実装方針:
- ルックアヘッドバイアスに注意すること
- 外部 API 呼び出しはリトライ・フェイルセーフを付与すること
- DuckDB の executemany の挙動（空リスト不可 等）に配慮すること

---

必要であれば README にサンプル .env.example、CI 実行方法、さらに詳しい API ドキュメント（各関数の引数と戻り値の表）を追加できます。どの情報を優先して追加しますか？