# KabuSys

日本株のデータパイプライン・リサーチ・AI支援・監査ログ・自動売買支援を目的としたライブラリ群です。DuckDB ベースのローカルデータレイクと J-Quants / OpenAI / kabuステーション 等の外部 API を組み合わせて、日次 ETL、ニュースセンチメント評価、ファクター計算、監査トレースを提供します。

---

## 主要な機能（概要）

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（duckdb）。
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）。
- ニュース収集・NLP
  - RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去、正規化）。
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）生成（バッチ、JSON Mode、リトライ/フォールバック）。
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成し市場レジーム（bull/neutral/bear）を算出して保存。
- リサーチ / ファクターモジュール
  - Momentum / Volatility / Value 等の定量ファクター計算。
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化など。
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 まで UUID ベースで追跡可能な監査テーブルを DuckDB に初期化・管理。
- 監視・実行支援（設定管理）
  - 環境変数での設定管理、.env 自動読み込み、プロセス監視用の閾値・ファイルパス設定。

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに組合せ型 `X | Y` を使用）
- DuckDB を利用可能な環境

1. リポジトリをクローン
   ```
   git clone <このリポジトリ>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   必要最低限の依存例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可能）。
   - 必須環境変数（少なくとも ETL を動かす場合）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime）
   - その他の環境変数（オプションやデフォルトあり）:
     - KABU_API_PASSWORD, KABU_API_BASE_URL
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 簡単な `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（基本例）

以下はライブラリをインポートして主要な処理を呼ぶ簡単なコード例です。

- DuckDB 接続を作成する例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を渡さない場合は今日を対象
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY で解決されます（引数で上書き可）
  written = score_news(conn, target_date=date(2026, 3, 19))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 19))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査用テーブル群が作成されます
  ```

- 研究／ファクター計算の呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  target = date(2026, 3, 19)
  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)
  value = calc_value(conn, target)
  ```

注意点:
- 多くの関数は Look-ahead バイアスを避けるため内部で date.today() や datetime.now() を直接参照しない設計です。必ず対象日を引数で与えるか、呼び出しタイミングを明確にしてください。
- OpenAI 呼び出しや外部 API 呼び出しはエラー時にフォールバックやリトライを行いますが、API キーが未設定だと ValueError を送出します。

---

## 主要 API / モジュール一覧（簡易）

- kabusys.config
  - Settings クラス（環境変数から各種設定を取得）
  - 自動 .env 読み込み（プロジェクトルート基準、.env → .env.local の順に読み込み）
- kabusys.data
  - pipeline.py: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl、ETLResult
  - jquants_client.py: J-Quants API ラッパー（fetch / save 関数、トークン管理・レートリミット・リトライ）
  - news_collector.py: RSS 取得・前処理・保存ロジック（SSRF 対策、XML パース安全化）
  - calendar_management.py: 市場カレンダー操作・営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ（シグナル / order_requests / executions）初期化ユーティリティ
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl.py: ETLResult の再エクスポート
- kabusys.ai
  - news_nlp.py: ニュースを集約して OpenAI でスコアリング（バッチ、検証、クリップ）
  - regime_detector.py: ma200 とマクロニュースを合成した市場レジーム判定
- kabusys.research
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys (パッケージ初期化)
  - __version__, __all__ 定義

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 配下を中心に記載）

- src/
  - kabusys/
    - __init__.py                — パッケージ定義
    - config.py                  — 環境変数 / .env 自動読み込み / Settings
    - ai/
      - __init__.py
      - news_nlp.py              — ニュースセンチメント（OpenAI）処理
      - regime_detector.py       — 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント（fetch/save）
      - pipeline.py              — ETL パイプライン（run_daily_etl 等）
      - etl.py                   — ETLResult 再エクスポート
      - news_collector.py        — RSS 収集・前処理
      - calendar_management.py   — 市場カレンダーの判定・更新ジョブ
      - quality.py               — データ品質チェック
      - stats.py                 — 統計ユーティリティ（zscore_normalize）
      - audit.py                 — 監査ログ DDL / 初期化ユーティリティ
    - research/
      - __init__.py
      - factor_research.py       — Momentum/Value/Volatility 等
      - feature_exploration.py   — 将来リターン / IC / 統計サマリー
    - ai/、research/ 以下に更に細かな実装

---

## 運用上の注意 / ベストプラクティス

- 環境分離:
  - KABUSYS_ENV は必ず設定してください（development / paper_trading / live）。特に live 環境では発注や実行ロジックの取り扱いに注意。
- API キー管理:
  - OpenAI / J-Quants のキーは秘匿情報です。`.env.local` や CI/CD の Secret 管理を推奨します。
- 自動 .env ロード:
  - ライブラリは起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
- DB バックアップ:
  - DuckDB ファイルは消失リスクに備えて定期的にバックアップを推奨します。
- テスト:
  - OpenAI 呼び出しや HTTP 関連はモック可能に設計されています（モジュール内の呼び出しを patch）ので、ユニットテストでは外部 API をモックして実行してください。

---

## 最後に

この README はコードベースの主要機能・導入・使用例を簡潔にまとめたものです。細かい挙動、SQL スキーマやプロンプトの詳細、エラー処理のポリシーなどは各モジュールの docstring を参照してください。追加の利用シナリオやデプロイ手順（systemd / cron / Docker 等）が必要であれば、その用途に合わせたドキュメントを別途作成できます。