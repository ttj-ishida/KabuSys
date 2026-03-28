# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、因子計算、監査ログなど、取引システムに必要な基盤処理をモジュール化して提供します。

---

## 主な概要

- 設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視。
- データ永続化には DuckDB を使用（監査用に専用 DuckDB を作るユーティリティあり）。
- J-Quants API からのデータ取得、RSS ニュース収集、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価などをサポート。
- 研究用モジュール（因子計算、将来リターン、IC 計算等）を含むため、研究／本番双方で利用可能。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証

- データ関連（kabusys.data）
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
  - ETL パイプライン（prices / financials / calendar の差分取得・保存・品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev trading day、calendar 更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策、正規化、トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
  - 監査ログ（signal_events / order_requests / executions テーブルと初期化ユーティリティ）
  - 汎用統計ユーティリティ（Z-score 正規化 等）

- AI 関連（kabusys.ai）
  - ニュース NLP（銘柄単位にまとめて LLM に送りセンチメントを ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク関数

---

## 必要要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそちらを利用してください。上記はコードから明示的に参照される主要な外部依存です。）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージのインストール
   - pip install duckdb openai defusedxml

   （プロジェクトをパッケージ化している場合は `pip install -e .` を利用できます。）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite path（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL: ログレベル（DEBUG, INFO, ...。デフォルト INFO）

   .env の書式は一般的な KEY=VALUE、`export KEY=VAL` 形式にも対応し、コメントやクォートも適切に処理されます。

4. データベース初期化（監査ログなど）
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的なユースケース）

以下は Python スクリプトとして使う際の簡単な例です。すべての例はプロジェクトルートで実行する想定です。

- DuckDB 接続の作成例:
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（prices / financials / calendar / 品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP スコアリング（ai_scores への書き込み）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
    print(f"書き込み銘柄数: {written}")

- 市場レジーム評価（market_regime テーブルへ書き込み）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは env または api_key 引数で指定

- 監査ログスキーマ初期化（既存接続へ）
  - from kabusys.data.audit import init_audit_schema
    conn = duckdb.connect("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)

- リサーチ用因子計算例
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))

- Z-score 正規化ユーティリティ
  - from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- カレンダー関連ユーティリティ（営業日判定）
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
    conn = duckdb.connect("data/kabusys.duckdb")
    is_td = is_trading_day(conn, date(2026, 3, 20))
    next_td = next_trading_day(conn, date(2026, 3, 20))

---

## 注意点 / 備考

- OpenAI を使う部分（news_nlp/regime_detector）は API 呼び出しの失敗に備え、フェイルセーフ（スコア 0.0 でフォールバック）やリトライを実装しています。テスト時は各モジュールの内部 _call_openai_api をパッチしてスタブ化できます。
- J-Quants クライアントはレート制御（120 req/min）やトークン自動リフレッシュを実装しています。get_id_token() は settings.jquants_refresh_token を利用します。
- ETL やニュース収集はルックアヘッドバイアスを防ぐため、target_date の扱いが慎重に設計されています（datetime.today()/date.today() を安易に参照しません）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンの互換性を考慮した実装が含まれています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                             # .env 自動読み込み / Settings
- ai/
  - __init__.py
  - news_nlp.py                          # ニュース NLP スコアリング（LLM 呼び出し、チャンク処理）
  - regime_detector.py                   # 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py               # マーケットカレンダー管理（営業日判定、更新ジョブ）
  - etl.py / pipeline.py                 # ETL パイプライン、run_daily_etl など
  - jquants_client.py                    # J-Quants API クライアント（fetch / save）
  - news_collector.py                    # RSS ニュース収集
  - quality.py                           # データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py                             # 統計ユーティリティ（zscore_normalize など）
  - audit.py                             # 監査ログテーブル定義・初期化
  - etl.py (小さな再エクスポートなど)
- research/
  - __init__.py
  - factor_research.py                   # モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py               # 将来リターン・IC・統計サマリー等

（上記はコードベースの主要モジュールを抜粋したものです）

---

## よくある運用ワークフロー例

1. 毎日深夜に run_daily_etl を実行して prices/financials/calendar を更新。
2. ETL 後にデータ品質チェックの結果を監視し、重大エラーがあればアラート（Slack 等）を送る。
3. ニュース収集 & ニュース NLP を定期的に実行して ai_scores を更新。
4. 市場レジーム（market_regime）を算出してリスク管理やポジションサイズ調整に反映。
5. 監査ログ（signal_events / order_requests / executions）を使ってシグナルから約定までをトレース可能に保つ。

---

必要があれば、README に含めるサンプル .env.example、要求パッケージの正確な requirements.txt、あるいは CLI ラッパーや systemd / cron 用の起動例も追加で作成できます。どの情報を優先して追加しますか？