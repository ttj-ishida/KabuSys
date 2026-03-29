KabuSys
=======

日本株向けのデータ基盤・研究・AI支援・監査・ETL を含む自動売買支援ライブラリ群です。  
本リポジトリは以下の主要機能をモジュール化して提供します：データ取得（J-Quants）、ETL パイプライン、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算・特徴量探索、データ品質チェック、監査ログ（トレーサビリティ）等。

プロジェクト概要
---------------
- 名前: KabuSys
- 目的: 日本株の自動売買システム構築を支援するライブラリ群（データ取得・ETL、研究用ファクター計算、ニュースNLP、レジーム判定、監査ログ、品質チェックなど）。
- 言語: Python（型ヒント多数、Python 3.10+ 推奨）
- 主な外部依存: duckdb, openai, defusedxml（他に標準ライブラリ多数）

主な機能一覧
-------------
- データ取得 / ETL
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー等）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合などを検出
- ニュース収集
  - RSS フィード取得、前処理、安全対策（SSRF対策・サイズ制限等）、raw_news への保存設計
- ニュースNLP（OpenAI）
  - 銘柄単位のニュース統合センチメントを ai_scores に書き込む（score_news）
  - マクロニュースの LLM ベース判定とETF MA乖離の組み合わせによる市場レジーム判定（score_regime）
  - OpenAI の JSON モードを利用、リトライや応答検証を実装
- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ、Zスコア正規化ユーティリティ
- 監査（Audit）
  - signal_events / order_requests / executions を中心とした監査ログスキーマ生成・初期化（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを UUID で保持
- 設定管理
  - 環境変数と .env 自動ロード（.env, .env.local。ルートは .git または pyproject.toml で探索）
  - 必須環境変数のラッパー（kabusys.config.settings）

セットアップ手順
----------------

1. Python と仮想環境
   - Python 3.10 以上を用意します（3.11 推奨）。
   - 仮想環境を作成・有効化します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要最低限の依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発用や追加パッケージがある場合は別途 requirements.txt を用意して pip install -r requirements.txt を実行してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を置くと自動で読み込まれます。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 最低限必要な環境変数（コードベースから）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime を使う場合）
   - DB パス（任意、デフォルトで data 以下を使用）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

4. DB 初期化（監査用）
   - 監査ログ用 DB を初期化するには:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成

使い方（簡単な例）
-----------------

- 設定読み取り
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などでアクセス可能

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクト（取得件数や品質問題を含む）

- ニュースセンチメントスコア取得（AI）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key="OPENAI_API_KEY")
  - n は書き込んだ銘柄数（ai_scores テーブルへ保存）

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - result = score_regime(conn, target_date=date(2026,3,20), api_key="OPENAI_API_KEY")

- 監査スキーマ初期化（既存接続に対して）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- データ品質チェックを個別に実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - issues は QualityIssue のリスト（各チェックの詳細を含む）

設定と挙動に関する補足
--------------------
- .env の自動ロード
  - パッケージの import 時点でプロジェクトルートを .git または pyproject.toml から探索し、.env を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境値の検証
  - settings.env は "development" / "paper_trading" / "live" のいずれかを要求し、不正値は ValueError。
  - settings.log_level は "DEBUG/INFO/WARNING/ERROR/CRITICAL" のみ受け付けます。
- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI の Chat Completions（gpt-4o-mini）を JSON モードで利用しています。API 呼び出しはリトライ/バックオフやレスポンス検証処理を含みます。
  - API キーを関数引数で渡すことも可能（テスト時の差し替えや安全性のため）。

ディレクトリ構成
---------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの集約と LLM スコアリング（score_news）
    - regime_detector.py         — マクロセンチメント + ETF MA で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / DuckDB 保存処理
    - pipeline.py                — ETL パイプラインと run_daily_etl 等
    - etl.py                     — ETLResult の公開
    - news_collector.py          — RSS 取得・正規化・保存ロジック
    - calendar_management.py     — マーケットカレンダー管理（営業日判定等）
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py     — calc_forward_returns, calc_ic, factor_summary, rank
  - ai, research, data ほかを横断するユーティリティ群や補助関数多数

開発上の注意点 / 設計方針（抜粋）
--------------------------------
- ルックアヘッドバイアス防止: 多くの関数で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや再現性を考えた設計となっています。
- 冪等性: J-Quants → DuckDB の保存は ON CONFLICT DO UPDATE により冪等に行います。監査ログ等も削除しない前提です。
- API 呼び出し: リトライ（指数バックオフ）、429/5xx ハンドリング、トークン自動リフレッシュなど実運用を想定した堅牢な実装。
- セキュリティ: RSS 取得では SSRF 対策、受信サイズ制限、defusedxml による XML パース等の安全策を組み込んでいます。

問題報告・貢献
--------------
バグ報告や機能要望は issue を立ててください。設計方針に沿った実装・テスト付きの PR を歓迎します。

ライセンス
---------
（このリポジトリに LICENSE が含まれていればここに記載してください）

最後に
------
この README はコードベースの主要機能と利用方法の概要をまとめたものです。実運用の際は .env.example を基に環境を整え、まずはローカルの DuckDB を用いて ETL と品質チェックを実行して動作確認することを推奨します。必要ならば使い方の具体的なスクリプトや CLI の追加を行ってください。