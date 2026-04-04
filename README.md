# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取り込み）、ニュースの NLP 評価（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注 → 約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants から株価日足、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分・バックフィル戦略、ページネーション対応、トークン自動リフレッシュ、レート制御・リトライ実装
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合（未来日付や非営業日データ）を検出
- ニュース収集・NLP
  - RSS 取得（SSRF対策、トラッキングパラメータ除去、XML 安全パース）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）集計
  - マクロニュースから市場センチメントを推定し市場レジーム（bull/neutral/bear）を算出
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定の階層的トレーサビリティ用テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数の優先順位による自動読み込み（パッケージ内での自動ロード実装あり）
  - 自動ロードを無効化するフラグあり（テスト時に便利）

---

## 要件

- Python 3.10+
- 主な依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス
  - J-Quants API（リフレッシュトークン必須）
  - OpenAI API（OPENAI_API_KEY 必須） — ニュース NLP / レジーム判定で使用

（プロジェクトに requirements.txt があればそちらを使ってください。上記はコード内から推測した主要依存です）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（推奨）
   - 例（venv）
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

3. パッケージのインストール（開発環境・編集可能インストール）
   ```
   pip install -e .
   ```
   もしくは依存を個別にインストール：
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（と必要なら `.env.local`）を配置します。自動読み込みは既定で有効です（CWD に依存せず package の位置からプロジェクトルートを探索して読み込み）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定が必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: ETL 使用時）
   - OPENAI_API_KEY: OpenAI の API キー（必須: news_nlp / regime_detector）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文執行等で使用）
   - Optional / 推奨:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

   .env の参考（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主なユースケース）

以下は Python スクリプト／REPL での基本的な呼び出し例です。すべての関数は duckdb の接続オブジェクト（kabusys.config.settings で指定されたパスを使うことが多い）を受け取ります。

- DuckDB 接続を作る例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（株価 / 財務 / カレンダーの差分取り込み）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア算出（ai_scores への書き込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーを引数で渡すことも可能（None なら環境変数 OPENAI_API_KEY を使用）
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

- 研究用ユーティリティ（ファクター計算など）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 設定・挙動の補足

- 環境変数自動ロード
  - モジュール kabusys.config はインポート時にプロジェクトルート（.git か pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で自動読み込みします（OS 環境変数が優先されます）。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- OpenAI / J-Quants 呼び出しのフェイルセーフ
  - ニュースの評価やレジーム判定で API 呼び出しが失敗した場合、多くはフォールバック（macro_sentiment=0.0 など）して処理を継続します。外部 API への依存による完全停止を避ける設計です。

- Look-ahead バイアス回避
  - ニュースウィンドウや価格取得では「target_date 未満 / 以前のデータのみ使用」など、バックテスト用にルックアヘッドバイアスを避ける実装方針が採られています。

- DuckDB の注意点
  - 一部の executemany は空リストを渡せない状況（古い DuckDB バージョン）を考慮した実装になっています。DuckDB のバージョンに依存する挙動に注意してください。

---

## ディレクトリ構成（主要ファイル）

（抜粋）プロジェクトの主要モジュール構造は以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py            # ニュース NLU（score_news）
      - regime_detector.py     # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch/save）
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - news_collector.py      # RSS 収集、前処理
      - calendar_management.py # マーケットカレンダー管理
      - quality.py             # データ品質チェック
      - stats.py               # 統計ユーティリティ（zscore_normalize 等）
      - audit.py               # 監査ログテーブル初期化
      - etl.py                 # ETLResult 再エクスポート
    - research/
      - __init__.py
      - factor_research.py     # ファクター計算（momentum/value/volatility）
      - feature_exploration.py # 将来リターン・IC・統計サマリー等
    - ai/
      - news_nlp.py
      - regime_detector.py

（上記は抜粋です。実際のファイル一覧は src/kabusys 以下で確認してください）

---

## 開発・テスト時のヒント

- 自動環境変数読み込みを無効化したいとき:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  または Windows では `set KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- OpenAI / J-Quants の呼び出し部分は内部で _call_openai_api / _request などを分離しているため、ユニットテストではこれらを unittest.mock.patch で差し替えやすくなっています。

- DuckDB の初期スキーマや監査テーブルなどは `kabusys.data.audit.init_audit_schema` / `init_audit_db` を使って初期化できます。

---

もし README に追記したい具体的なコマンド例（cron ジョブ設定、Dockerfile、CI 設定など）や、より詳細な .env.example を希望される場合は教えてください。必要に応じてサンプル .env.example を作成します。