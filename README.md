KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを含みます。

主な目的
- J-Quants API を用いたデータ取得と DuckDB への永続化（冪等）
- RSS ニュース収集と OpenAI による銘柄・マクロのセンチメント評価
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 発注・約定フローの監査ログ（トレーサビリティ）テーブル作成ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応、リトライ・レートリミッタ付き）
  - 差分更新、バックフィル、品質チェック、日次パイプライン（run_daily_etl）
- ニュース処理 / NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - OpenAI（gpt-4o-mini を想定）で銘柄ごとのニュースセンチメント（score_news）
  - OpenAI によるマクロ記事センチメントを用いた市場レジーム判定（score_regime）
- 研究用（Research）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env（.env.local）自動ロード（プロジェクトルート検出）、環境変数読み取り用 Settings オブジェクト

セットアップ手順（開発環境）
- 前提
  - Python 3.10+（typing の "X | Y" 構文を使用）
  - DuckDB, openai SDK, defusedxml などの依存が必要

- 仮想環境作成（例）
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

- 必要パッケージ（例）
  - pip install duckdb openai defusedxml
  - 他に標準ライブラリ以外のパッケージが必要な場合はプロジェクト内の requirements.txt を参照してください（このリポジトリのサンプルには明示的な requirements ファイルは含まれていません）。

- 環境変数 / .env
  - プロジェクトルートに .env（および .env.local）を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 必須環境変数（少なくとも以下を設定してください）:
    - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
    - SLACK_BOT_TOKEN: Slack 送信用トークン（本コードベースの一部機能が利用する場合）
    - SLACK_CHANNEL_ID: Slack チャネル ID
    - KABU_API_PASSWORD: kabu ステーション API のパスワード（オプションだが実運用で使用する場合は必須）
    - OPENAI_API_KEY: OpenAI を用いる機能を呼ぶ場合は必須（score_news, score_regime など）
  - 任意 / デフォルト値:
    - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
    - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）

使い方（基本例）
- 設定の読み取り
  - from kabusys.config import settings
  - settings.jquants_refresh_token などでアクセス

- DuckDB 接続を作成（例）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存（score_news）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  - print(f"書き込み銘柄数: {written}")

- 市場レジームを判定して market_regime に保存（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - ret = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  - print(ret)

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算（例）
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - 正規化: from kabusys.data.stats import zscore_normalize

注意点 / 設計上のポイント
- ルックアヘッドバイアス対策:
  - 多くの関数は date.today() / datetime.today() を直接参照せず、target_date 引数を受け取る設計です。バックテスト用途では適切な日付を渡してください。
- 冪等性:
  - save_* 系関数は ON CONFLICT DO UPDATE 等で冪等な保存を行います。
- フェイルセーフ:
  - OpenAI API の失敗時やニュースがない場合はゼロスコアやスキップで継続する設計（致命的な例外は基本的に上位に伝播する処理のみ）。
- テスト / モック:
  - OpenAI など外部呼び出し部分は内部関数を patch してテスト可能なように実装されています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP スコアリング（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント、保存関数
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult 再エクスポート
    - news_collector.py                 — RSS ニュース収集
    - calendar_management.py            — マーケットカレンダー管理（営業日判定等）
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（z-score）
    - audit.py                          — 監査ログテーブル作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py                — Momentum/Value/Volatility 等の計算
    - feature_exploration.py            — 将来リターン / IC / 統計サマリー 等
  - ai and research など他モジュール多数（ETL・研究・実行層は分離設計）

環境変数の自動読み込み
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動で読み込みます。
- 読み込み順序: OS 環境 > .env.local > .env
- 自動読み込みを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

依存関係（主な外部パッケージ）
- duckdb
- openai
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging, etc.）

拡張と統合
- Slack 通知、kabu ステーション（発注）統合、監視 DB（sqlite）などと組み合わせて運用可能です。実運用では KABU_API_PASSWORD や証券会社側の API 設定、適切な権限・テストを行ってください。

トラブルシューティング
- OpenAI 呼び出しに失敗する場合は OPENAI_API_KEY の設定を確認してください。API レート制限・429 や 5xx はライブラリ側でリトライロジックがありますが、頻繁に失敗する場合は API キーやネットワークを確認してください。
- J-Quants API の 401 は自動でリフレッシュを試みます（設定されたリフレッシュトークンが有効である必要あり）。
- DuckDB のファイルが作成されない場合は DUCKDB_PATH の親ディレクトリのパーミッションを確認してください。

ライセンス・貢献
- 本リポジトリにライセンスファイルがある場合はそちらを参照してください。貢献・バグ報告は issue / PR で受け付けます。

以上が簡潔な README です。使い方の具体例や CI / デプロイ手順が必要であれば、利用シナリオ（ローカル ETL / バックテスト / 本番運用）を教えてください。必要に応じて README を拡張します。