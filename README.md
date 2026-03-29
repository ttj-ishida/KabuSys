# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ、監視／発注連携までを含むコンポーネントがまとまっています。

## 特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出（quality モジュール）
- カレンダー管理
  - JPX カレンダーの更新、営業日判定、次/前営業日取得（calendar_management）
- ニュース収集 & NLP
  - RSS 収集（SSRF対策、サイズ制限、トラッキング除去）
  - OpenAI によるニュースセンチメント（ai.news_nlp.score_news）
  - 市場マクロセンチメントとMA乖離を合成した市場レジーム判定（ai.regime_detector.score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research フォルダ）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- 監査ログ（audit）
  - シグナル→発注→約定のトレーサビリティ用スキーマ定義と初期化（DuckDB）
- J-Quants クライアント
  - レート制限、リトライ、トークン自動リフレッシュ、取得ユーティリティ（data.jquants_client）
- 設定管理
  - .env/.env.local から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト（kabusys.config.settings）で環境変数にアクセス

---

## セットアップ手順（開発環境向け）

※本リポジトリに requirements.txt / pyproject.toml がある前提での一般的手順を示します。

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または pyproject.toml を使う場合: pip install -e .
4. 環境変数を設定
   - プロジェクトルートに `.env`（およびローカルで上書きする場合は `.env.local`）を作成してください。
   - 自動読み込みはデフォルトで有効：`.env` → `.env.local` の順に読み込まれ、OS 環境変数が保護されます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

環境変数一覧（必須/任意）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（data.jquants_client.get_id_token に使用）
  - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（通知機能を使う場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（通知機能を使う場合）
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
- 任意／デフォルトあり
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 動作モード（development / paper_trading / live）。デフォルト development
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト INFO
- OpenAI
  - OPENAI_API_KEY: News NLP / Regime 判定に必要（score_news, score_regime を使用する場合）

例（.env の一部）
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxx
    SLACK_BOT_TOKEN=xoxb-xxxx
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要な実行例）

以下は基本的な実行例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続の用意（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数参照
  print(f"scored {count} stocks")
  ```

- 市場レジームスコアを算出して market_regime テーブルへ書き込み（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定が適用されます
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点
- AI モジュール（news_nlp、regime_detector）は OpenAI の Chat Completions（gpt-4o-mini 等、JSON mode）を使用します。API のレスポンスフォーマットが要件を満たさない場合や失敗した場合はフェイルセーフとして 0.0（中立）やスキップを返す設計になっています。
- ETL / jquants_client は API レート制限（120 req/min）や 401 自動リフレッシュ、リトライロジックを備えています。
- ETL / データ品質チェックは部分失敗を許容し、結果として ETLResult にエラーや品質問題を集約して返します。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールを示します（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py                  — score_news の公開
    - news_nlp.py                  — ニュースセンチメント（OpenAI呼び出し、バッチ処理、検証）
    - regime_detector.py           — MA200 とマクロニュースの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存・認証・RateLimiter）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS 収集 / 前処理 / 保存用ユーティリティ
    - calendar_management.py       — マーケットカレンダーの管理（営業日、更新ジョブ）
    - stats.py                     — zscore 正規化などの統計ユーティリティ
    - audit.py                     — 監査スキーマ初期化 / DB 初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py       — 将来リターン計算 / IC / 統計サマリ
  - research/...                   — 研究用ユーティリティ群
  - (その他: strategy / execution / monitoring パッケージが __all__ に含まれる想定)

この README はコードベースの主要意図と利用方法をまとめたものです。詳細は各モジュールの docstring を参照してください（各関数に設計方針や副作用、フェイルセーフの挙動が記載されています）。

何か追加で README に盛り込みたい情報（実行例の拡張、設定例のテンプレート、CI/migrations の手順など）があれば教えてください。