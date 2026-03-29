# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
市場データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー追跡）などを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス回避（date.today()/datetime.today() を内部ループで参照しない設計）
- DuckDB をデータ層に使用（ローカル分析に最適化）
- 冪等性（ETL / 保存処理は ON CONFLICT/DELETE→INSERT 等で安全）
- 外部 API 呼び出しはリトライやレート制御を備えた実装
- セキュリティ対策（RSS の SSRF対策・XML攻撃対策等）

## 機能一覧
- 環境・設定管理
  - 自動 .env ロード（プロジェクトルートを探索）
  - 必須設定の検査（設定未指定でエラーを出すユーティリティ）
- データ ETL（kabusys.data.pipeline）
  - J-Quants API を用いた株価・財務・カレンダーの差分取得と保存
  - run_daily_etl による日次パイプライン（品質チェック含む）
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合の検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・カレンダー更新ジョブ
- ニュース収集と前処理（kabusys.data.news_collector）
  - RSS 取得、URL正規化、SSRF対策、raw_news への保存向け整形
- AI（OpenAI）連携（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日MAとマクロニュースで市場レジーム判定
  - 安定したリトライ・JSON 検証ロジック
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - 将来リターン、IC、統計サマリー、z-score 正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を用いた発注〜約定までのトレーサビリティ
  - init_audit_db で DuckDB データベース初期化をサポート
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh_token → id_token）、レート制御、リトライ、ページネーション対応
  - 保存用ユーティリティ（raw_prices/raw_financials/market_calendar への保存）

---

## セットアップ手順（開発者向け）

前提
- Python 3.10 以上（typing の "|" 型表記を使用）
- Git レポジトリルートに .env / .env.local を配置可能

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt はプロジェクトに合わせて用意してください。上記は主要依存の例です。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env):
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabu API（kabuステーション）関連
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルトは上記

   # Slack（通知等に使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行モードとログレベル
   KABUSYS_ENV=development       # development / paper_trading / live
   LOG_LEVEL=INFO

   # OpenAI
   OPENAI_API_KEY=sk-...
   ```

4. DuckDB データベースの初期化（監査ログ用など）
   - Python REPL、またはスクリプトで:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```
   - 既存接続へスキーマだけ適用する場合は init_audit_schema(conn)

---

## 使い方

以下は代表的な利用例です。実行前に必須の環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定してください。

- ETL（日次パイプライン）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメントをスコアして ai_scores に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  num_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written {num_written} scores")
  conn.close()
  ```

- 市場レジーム（bull/neutral/bear）を算出して market_regime に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  conn.close()
  ```

- 監査ログ DB を初期化する（別途監査用 DB を用意）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn をアプリの監査ログ保存に利用
  conn.close()
  ```

- J-Quants クライアントを直接利用して日次株価を取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from datetime import date
  rows = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

注意点
- settings.* のプロパティは未設定時に ValueError を送出します（必須設定の検知に有効）。
- AI 呼び出し（OpenAI）は JSON mode を使いレスポンスを厳密に検証します。API キーは OPENAI_API_KEY または関数引数で指定してください。
- ETL / AI 呼び出し処理はいずれもフェイルセーフ設計で、API失敗時は可能な処理を継続するよう設計されています（ただし致命的エラーはログや例外で通知されます）。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの Python パッケージは `kabusys`。主なモジュール:

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py
    - 環境変数読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュースセンチメント算出（OpenAI）
    - regime_detector.py   -- ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得・保存）
    - pipeline.py          -- ETL パイプラインと run_daily_etl
    - etl.py               -- ETLResult 再エクスポート
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - news_collector.py    -- RSS 取得・前処理
    - quality.py           -- データ品質チェック
    - stats.py             -- 統計ユーティリティ（z-score 等）
    - audit.py             -- 監査ログスキーマ初期化・ヘルパー
  - research/
    - __init__.py
    - factor_research.py   -- Momentum / Value / Volatility ファクター計算
    - feature_exploration.py -- forward returns / IC / summary / rank 等

（上記は主要部分の抜粋です。サブモジュールや細かいユーティリティはソース内にあります。）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - パッケクトは自動でプロジェクトルート（.git または pyproject.toml の位置）を探索して `.env`/`.env.local` を読み込みます。テストや特殊用途で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI の呼び出しが失敗する
  - `OPENAI_API_KEY` が未設定だと ValueError が送出されます。キーを環境変数に設定するか、関数引数で明示的に渡してください。
  - API 呼び出しは 429/ネットワーク/5xx をリトライする仕組みがありますが、上限に達すると警告を出してスキップする動きになります。

- J-Quants API エラー
  - get_id_token() はリフレッシュトークンを使って id_token を取得します。`JQUANTS_REFRESH_TOKEN` を設定してください。
  - レート制御（120 req/min）やリトライが組み込まれています。

---

## 開発・拡張に関するメモ
- DuckDB を用いることで SQL を直接書いて高速に集計・分析可能です。ETL・品質チェック・研究用関数はすべて DuckDB 接続を受け取る形で実装されています。
- AI 部分はテスト容易性を考慮し、内部の HTTP 呼び出しや API 呼び出しポイントをモックできるように設計されています（関数を patch して代替実装を注入可能）。
- Look-ahead バイアスを避けるため、target_date を明示して処理する API を優先してください。

---

必要であれば、README に追加で以下の情報を追記できます：
- 詳細な依存関係（requirements.txt の内容）
- CI / テストの実行方法（pytest 等）
- 実運用時のデプロイ手順（systemd / containerization / スケジューリング）
- SQL スキーマ定義一覧（テーブル構造の完全ドキュメント）

ご希望があれば追記・整備します。