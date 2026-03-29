# KabuSys — 日本株自動売買システム（README）

KabuSys は日本株のデータプラットフォーム、リサーチ、ニュース NLP、レジーム判定、監査ログなどを備えた自動売買支援ライブラリです。DuckDB ベースのローカルデータベースを利用し、J-Quants / OpenAI / RSS 等の外部サービスと連携する ETL・品質チェック・AI スコアリング機能を提供します。

---

## プロジェクト概要

主な目的：
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL。
- ニュース記事の収集と OpenAI を用いた銘柄別センチメント（ai_score）算出。
- ETF（1321）移動平均乖離とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定。
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ。
- 発注〜約定に至る監査ログ（audit スキーマ）によるトレーサビリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）による監査。

設計上の特徴：
- Look-ahead バイアス回避のため、内部で現在時刻を直接参照しない処理を多用。
- 冪等性（ON CONFLICT やユニークキー）を考慮した DB 保存ロジック。
- 外部 API 呼び出しに対する堅牢なリトライ・レート制御・フェイルセーフ（失敗時はスキップして継続）設計。
- セキュリティ対策（RSS の SSRF 対策、defusedxml、受信サイズ制限 など）。

---

## 機能一覧（抜粋）

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証, ページネーション, レート制限, 保存関数）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS 取得・正規化・SSRF 対策）
  - 品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）

- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で算出し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを合成して market_regime に保存

- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
  - zscore_normalize の再エクスポート

- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を自動読み込み。無効化可能）
  - settings オブジェクト経由で設定を取得（必須値は _require により明示エラー）

---

## 必須環境変数 / 設定

主要な環境変数（README で示す代表例）：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリングで使用）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルトは development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視データ等）パス（デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動読み込み：
- パッケージ import 時にプロジェクトルート（.git か pyproject.toml があるディレクトリ）を探索し、
  .env → .env.local の順で自動読み込みを行います（OS 環境変数を上書きしない挙動）。
- テスト等で自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（最小）
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-xxxxxxxx
KABU_API_PASSWORD=your_kabu_pwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development

---

## セットアップ手順

1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (macOS / Linux)
     - .venv\Scripts\activate     (Windows PowerShell)

2. 依存パッケージのインストール
   - pip install -r requirements.txt
   - または開発中は:
     - pip install -e ".[dev]"  （プロジェクトが setuptools/pyproject を提供する場合）
   - 主な依存:
     - duckdb
     - openai (新しい SDK を使用する実装に合わせる)
     - defusedxml
     - その他（標準ライブラリで賄う実装が多い）

3. 環境変数設定
   - プロジェクトルートに `.env` を作成して必須変数を設定するか、
   - CI / 実行環境のシークレットとして環境変数を注入する。

4. DuckDB 初期スキーマ（監査用）の初期化（必要に応じて）
   - Python REPL などで実行例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 既存接続に対してスキーマだけ追加する場合:
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

5. テスト用 API キー / モック
   - OpenAI 呼び出しはモック可能（ユニットテストで _call_openai_api を差し替え）。
   - J-Quants API は実際のトークンを使用するか、テスト用にモックしてください。

---

## 使い方（基本例）

以下は Python スクリプト内から主要機能を呼び出す例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

- 日次 ETL を実行する（株価・財務・カレンダー・品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントをスコアして ai_scores に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か引数で指定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み銘柄数:", n_written)

- 市場レジームを判定して market_regime に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算（研究用）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

- 監査 DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って発注/約定のログを記録・検索可能

注意点：
- OpenAI 呼び出しはネットワーク失敗やレート制限に対してリトライやフォールバック（スコア=0）を行いますが、APIキーは必須です（score_news/score_regime の api_key 引数か環境変数 OPENAI_API_KEY を設定）。
- ETL / ニュース収集は外部サービスと通信するため、実行前に必須の認証情報（J-Quants, OpenAI 等）を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py                — パッケージ初期化・バージョン
  - config.py                  — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py   — 市場カレンダー管理
    - news_collector.py        — RSS 収集 / 前処理 / 保存ロジック
    - quality.py               — データ品質チェック（QualityIssue）
    - audit.py                 — 監査ログ（テーブル定義・インデックス・初期化）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py       — ファクター（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー等
  - ai/（上記）
  - research/（上記）

---

## 実装上の注意・ベストプラクティス

- ルックアヘッドバイアス回避
  - 多くの関数は target_date を明示的に受け取り、内部で datetime.today() を直接参照しません。バックテストや再現性のため、必ず target_date を明示してください。

- OpenAI / 外部 API の扱い
  - API 呼び出しはリトライとバックオフをしており、失敗時は安全側のデフォルト（例: macro_sentiment=0.0）で継続します。ユニットテスト時は _call_openai_api をモックして deterministic な戻り値を返すことを推奨します。

- ニュース収集のセキュリティ
  - RSS フェッチ時はスキームチェック・プライベートアドレス検査・リダイレクト時検査・受信サイズ上限・defusedxml による XML セキュリティ対策を実施しています。

- DuckDB 互換性
  - DuckDB のバージョン差や executemany の制約を考慮した実装（空の params の扱い等）を行っています。

---

## 開発・テスト時のヒント

- 環境変数の自動読み込みを無効にする場合：
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出しのモック例（pytest など）：
  monkeypatch.setattr("kabusys.ai.news_nlp._call_openai_api", fake_fn)

- J-Quants クライアントのテストでは get_id_token や _request をモックして HTTP を行わないようにする。

---

## ライセンス・貢献

この README はコードベースの説明を目的としています。実際のプロジェクトでは LICENSE と CONTRIBUTING ガイドを用意してください。

---

必要であれば、より具体的なセットアップ（requirements.txt の中身想定、Dockerfile、systemd タイマー / cron での定期実行例、Slack 通知のサンプルコードなど）も追加します。どの情報がさらに必要か教えてください。