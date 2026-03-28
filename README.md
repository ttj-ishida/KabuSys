# KabuSys

日本株向けの自動売買 / データプラットフォームのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（発注 → 約定トレース）等の機能を提供します。

バージョン: 0.1.0

---

## 主な特徴 (Features)

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション・再試行・レート制御を実装

- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip/サイズ制限

- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを集約して LLM（gpt-4o-mini）でセンチメント評価し ai_scores に格納
  - レート制限・リトライ・レスポンス検証・JSON Mode 対応

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成してレジーム判定（bull/neutral/bear）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 系ファクター、将来リターン計算、IC（Spearman rank）計算、Z-score 正規化など

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出、QualityIssue オブジェクトで結果を返却

- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査テーブルの作成・初期化（DuckDB）
  - 発注フローのトレーサビリティを UUID 階層で確保

- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）と Settings オブジェクト（環境変数アクセス）を提供

---

## 必要条件 (Requirements)

最低限の実行に必要な Python パッケージ（代表例）:

- Python 3.9+
- duckdb
- openai
- defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## インストール (Setup)

1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS / Linux: source .venv/bin/activate

2. 依存パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトのパッケージとして editable install があれば）pip install -e .

3. 環境変数 / .env の準備:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必要な環境変数（主なもの）

以下はこのコードベースで参照される主な環境変数と既定値の例です。`.env.example` を用意してそれを元に `.env` を作成してください。

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants API 用のリフレッシュトークン。jquants_client.get_id_token で使用。

- KABU_API_PASSWORD (必須)  
  - kabu ステーション API のパスワード。

- KABU_API_BASE_URL (任意)  
  - デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  - Slack 通知用 Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  - 通知先チャンネル ID。

- DUCKDB_PATH (任意)  
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  - デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  - 許容値: development / paper_trading / live  
  - デフォルト: development

- LOG_LEVEL (任意)  
  - 許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL  
  - デフォルト: INFO

- OPENAI_API_KEY (OpenAI を使う処理に必須)  
  - news_nlp.score_news, regime_detector.score_regime などで使用。引数で上書き可能。

---

## 使い方 (Usage)

以下は代表的なユースケースの呼び出し例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続の例:
  ```
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行:
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```
  - J-Quants の認証は settings.jquants_refresh_token を用いる（.env に設定）。

- ニュース NLU（AI）でスコアを付ける:
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {n_written}")
  ```
  - API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定。

- 市場レジーム判定:
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- リサーチ / ファクター計算:
  ```
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化:
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # parent dir will be created
  ```
  または既存 conn にテーブルを追加:
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 設定参照:
  ```
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)
  ```

テスト・モックについて:
- OpenAI 呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替え可能（テスト用に容易にモックできる設計）。

---

## 注意事項 / セキュリティ

- .env に API トークンを保存する際はリポジトリにコミットしない（.gitignore に追加）。
- NEWS RSS の取得では SSRF 対策、Response サイズ制限、gzip 解凍サイズ検査などを行っていますが、運用時は追加監視を推奨します。
- OpenAI / J-Quants など外部 API のレート制限・利用規約に従ってください。
- KABUSYS_ENV によって本番 / ペーパー / 開発の挙動切替を行います。live 環境では特に注意して使用してください。

---

## ディレクトリ構成

主要なファイル・モジュールとその概要:

- src/kabusys/
  - __init__.py (パッケージ情報、__version__ = "0.1.0")
  - config.py
    - 環境変数の自動ロード（.env / .env.local）、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でセンチメント評価し ai_scores に保存
    - regime_detector.py
      - ETF(1321)のMA乖離 + マクロニュースLLMで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar の管理、営業日判定、next/prev/get_trading_days 等
    - etl.py
      - ETLResult (再エクスポート)
    - pipeline.py
      - 日次 ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
    - jquants_client.py
      - J-Quants API クライアント（fetch / save ロジック、ID トークン管理、RateLimiter）
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策、ID 生成）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value の計算（prices_daily / raw_financials 参照）
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、ランク関数

（上記は主要モジュールのみを抜粋しています。詳細はソースを参照してください）

---

## 開発・貢献

- バグ報告・プルリクエストはリポジトリの Issue / PR を利用してください。
- テストは外部 API を直接叩かないようにモックして実装してください（OpenAI / J-Quants 呼び出しの差し替えポイントあり）。

---

## ライセンス

- 本 README はリポジトリに合わせて適切なライセンスを選択してください（このソースにライセンス表記がない場合は運用ルールに従ってください）。

---

以上がプロジェクトの概要・セットアップ・使い方・構成のまとめです。README に追記したい具体的な実行コマンド例や .env.example のテンプレートが必要であれば作成します。