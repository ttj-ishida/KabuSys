# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなど、取引システムを構成する主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・レート制御・リトライ付き）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去、サイズ上限）
  - OpenAI を用いたニュースセンチメント（銘柄ごと、日次ウィンドウ）スコアリング（score_news）
  - マクロニュースとETF（1321）の MA200乖離を合成した市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルのスキーマ初期化（init_audit_schema / init_audit_db）
  - UUID ベースの冪等トレーサビリティ設計

- 設定管理
  - .env 自動読み込み（プロジェクトルートを基準に `.env` / `.env.local`、OS 環境変数優先）
  - Settings クラス経由で環境変数へアクセス（kabusys.config.settings）

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+（型ヒントの union 演算子や typing の使用から想定）

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 主要な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（必要に応じて `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の主要環境変数（コード内 Settings を参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（システム内で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack のチャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で利用）
- その他（任意）:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/etc、デフォルト INFO）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（主要 API と利用例）

以下はライブラリを Python から直接利用する基本例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す DuckDBPyConnection）を受け取る設計です。

- ETL を実行（全体パイプライン）
  - 目的: 日次で J-Quants からデータを取得して保存し、品質チェックまで実行
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
    ```

- ニュースセンチメントのスコアリング（AI）
  - score_news は OpenAI の API キーを環境変数 `OPENAI_API_KEY` から読むか、引数で渡せます。
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {written} symbols")
    ```

- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))
    ```

- 監査ログ DB 初期化
  - init_audit_db は監査用の DuckDB を作成しスキーマを初期化して接続を返します。
  - 例:
    ```python
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    ```

- 研究用関数（ファクター計算等）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic などは DuckDB 接続と target_date を渡して呼び出します。

注意:
- OpenAI 呼び出しはネットワーク障害やレート制限を考慮したリトライ実装が含まれていますが、API キーは必須です（引数で渡すことも可能）。
- ETL/スコアリングの実行は通常 cron / Airflow / 任意のバッチジョブとして運用します。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys 以下）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動ロードと Settings クラス
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの記事単位・銘柄スコア算出（score_news）
  - regime_detector.py — マクロニュース + ETF MA200 で市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 系）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS フィード取得と前処理
  - calendar_management.py — 市場カレンダー管理（営業日ロジック、calendar_update_job）
  - quality.py — データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ定義・初期化（init_audit_schema / init_audit_db）
- src/kabusys/research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## 設計上の注意点 / 運用上のヒント

- Look-ahead bias 防止
  - 多くの関数は内部で date.today() を直接参照せず、target_date を受け取る設計になっています。バックテストや再現性のため、明示的に日付を渡してください。

- 冪等性
  - ETL の保存操作や監査ログの初期化は冪等に扱う（ON CONFLICT/DO UPDATE、PK チェックなど）。

- エラー処理
  - 外部 API 呼び出し（J-Quants / OpenAI）はリトライ処理やフォールバック（マクロスコア未取得時は 0.0 など）を備えています。重大なエラーはログに記録され、ETL は可能な限り処理を継続します。

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を含む場所）を基準に `.env` と `.env.local` を自動読み込みします。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## テストと拡張

- 各モジュールは外部依存（OpenAI 呼び出しや HTTP）を容易にモックできるように設計されています（内部の _call_openai_api や _urlopen 等はテストで差し替え可能）。
- 研究用関数は外部ライブラリに依存せず純粋な Python / DuckDB SQL で実装されているため、解析ワークフローへの組み込みや Jupyter での探索に適しています。

---

README の内容はコードの現状に基づくサマリです。さらに実行スクリプト、CI、デプロイ、Slack 通知や kabuステーション連携（実売買機能）を追加する場合は別途ドキュメントを用意してください。疑問点や使い方サンプルのリクエストがあれば具体例を追加します。