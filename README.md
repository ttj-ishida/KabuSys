# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせて、データ収集（ETL）、データ品質チェック、ニュースセンチメント、マーケットレジーム判定、監査ログ、研究用ファクター計算などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要な呼び出し例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォーム兼研究・自動売買の基盤ライブラリです。  
主に以下を目的としています。
- J-Quants API から株価・財務・カレンダーを安全に取得・保存（DuckDB）
- RSS ニュースの収集と前処理（SSRF・サイズ制限・トラッキング除去等に配慮）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- 日次 ETL パイプライン、品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算・特徴量探索・IC 計算などの研究ユーティリティ
- 発注・約定に至る監査ログスキーマ（監査トレーサビリティ）

設計上の特徴:
- ルックアヘッドバイアスを避ける（API呼び出しや日付判定で現在日時を不用意に参照しない）
- 冪等性重視（DB 保存は ON CONFLICT などで重複対策）
- ネットワーク安全対策（RSS の SSRF 防止、API のリトライ・レート制限）
- テストしやすさ（API 呼び出し箇所を差し替え可能）

---

## 機能一覧

主な機能（モジュール）:
- kabusys.config
  - .env / 環境変数の読み込み・検証。自動でプロジェクトルートの .env / .env.local を読み込む（無効化可能）。
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（株価・財務・カレンダー等）
  - DuckDB へ安全に保存する save_* 関数
  - レート制御、リトライ、トークンリフレッシュを内蔵
- kabusys.data.pipeline / etl
  - 日次 ETL パイプライン実装（run_daily_etl 等）
  - 部分的な ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.news_collector
  - RSS 取得・正規化・前処理・raw_news への保存
  - SSRF / gz bomb / トラッキング除去に配慮
- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- kabusys.data.calendar_management
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.audit
  - 発注・約定の監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - ニュースを銘柄別に集約して OpenAI でセンチメントを算出し ai_scores に保存
- kabusys.ai.regime_detector
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを統合して市場レジーム（bull / neutral / bear）を算出
- kabusys.research
  - ファクター計算（momentum/value/volatility）や特徴量探索（forward returns / IC / summary）
- kabusys.data.stats
  - zscore_normalize 等の汎用統計ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の union | を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS）

主要な依存パッケージ（最低限）:
- duckdb
- openai
- defusedxml

インストール例（pip を使用）:
1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 開発インストール（プロジェクトルートで）
   - pip install -e .             # もしパッケージの setup/pyproject があれば
   - pip install duckdb openai defusedxml

（注）実際の requirements.txt / pyproject.toml に従って依存をインストールしてください。

---

## 環境変数（.env）と設定

KabuSys は環境変数から各種設定を読み込みます。プロジェクトルート（.git または pyproject.toml の親）を自動検出して `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants 用リフレッシュトークン。jquants_client.get_id_token の取得に使用。
- OPENAI_API_KEY (必須 for AI機能)  
  - OpenAI API キー。news_nlp / regime_detector で使用。
- KABU_API_PASSWORD (必須 if kabu API を使う場合)  
  - kabuステーション API パスワード。
- KABU_API_BASE_URL (任意)  
  - kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）。
- SLACK_BOT_TOKEN (必須 if Slack通知を使う場合)  
- SLACK_CHANNEL_ID (必須 if Slack通知を使う場合)
- DUCKDB_PATH (任意)  
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  - 監視系などで使用する SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)  
  - "development" / "paper_trading" / "live" のいずれか（デフォルト: development）
- LOG_LEVEL (任意)  
  - "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）

.env のパース機能は以下をサポート:
- export KEY=val 形式
- シングル/ダブルクォートとエスケープ
- コメント行・インラインコメント（スペース前の '#' をコメントとみなす等）

例 (.env):
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
OPENAI_API_KEY="sk-..."
KABU_API_PASSWORD="your_kabu_pass"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な呼び出し例）

以下はライブラリを直接呼び出す簡単な例です。適宜 logging の設定や DB 初期化を行ってください。

1) DuckDB 接続の例
- duckdb を使い接続:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL の実行
- from kabusys.data.pipeline import run_daily_etl
- res = run_daily_etl(conn, target_date=some_date)
- res.to_dict() で詳細を取得

3) ニュースセンチメントのスコア付け（AI）
- from kabusys.ai.news_nlp import score_news
- cnt = score_news(conn, target_date=some_date, api_key=None)  # api_key None -> OPENAI_API_KEY 環境変数を使用

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date, api_key=None)

5) 監査ログスキーマ初期化
- from kabusys.data.audit import init_audit_db, init_audit_schema
- # 専用 DB を作る場合:
  - audit_conn = init_audit_db("data/audit.duckdb")
- # 既存接続にスキーマを追加する場合:
  - init_audit_schema(conn, transactional=True)

6) カレンダー関連ユーティリティ
- from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days, calendar_update_job
- is_trading_day(conn, date(2026, 1, 1))
- next_trading_day(conn, date(2026, 1, 1))
- calendar_update_job(conn)

7) 研究用ユーティリティ
- from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic
- momentum = calc_momentum(conn, target_date)

（注）AI を使う機能は OpenAI API 呼び出しを行うため、API キーと通信可能な環境が必要です。API 呼び出しは失敗を全面的に抑止せず、フェイルセーフ動作（デフォルトスコア 0 等）を実装している箇所もあります。ログを確認してください。

---

## 実運用上の注意

- DuckDB の executemany 等の挙動やバージョン依存性に注意してください（コード内に互換性対策の記述があります）。
- J-Quants のレート制限（120 req/min）に合わせた RateLimiter を実装済みです。過負荷を避けるため、複数プロセスからの同時多数リクエストには注意してください。
- RSS 取得は SSRF や大容量攻撃に対する保護（スキーム検査、プライベートIP検査、サイズ上限、gzip展開後再チェック等）を行っていますが、運用環境での追加対策（プロキシやネットワーク制限）を推奨します。
- AI（OpenAI）呼び出しはコストがかかります。バッチサイズやモデル選択（gpt-4o-mini）を運用方針に合わせて調整してください。
- 本ライブラリ単体は発注（実際にブローカーへ注文送信）を行うモジュールを含みません。発注ロジックは監査テーブル等を利用して別モジュールで実装することが想定されています。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ配下の主なファイル・モジュール構成（src/kabusys）です。

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py           # ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py    # MA200 とマクロセンチメントで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py     # J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py           # ETL パイプライン（run_daily_etl 他）
  - etl.py                # ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py     # RSS 取得・前処理・raw_news 保存
  - calendar_management.py# 市場カレンダー管理（営業日判定等）
  - quality.py            # データ品質チェック
  - stats.py              # 統計ユーティリティ（zscore_normalize）
  - audit.py              # 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py    # momentum/value/volatility の計算
  - feature_exploration.py# forward returns / IC / factor summary / rank

（完全なファイル一覧はソースツリーを参照してください）

---

もし README に含めてほしい追加の項目（CLI 実行例、CI 設定、サンプル .env.example、ユニットテスト実行手順 など）があれば教えてください。必要に応じて追記します。