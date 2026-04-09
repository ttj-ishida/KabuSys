# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）→ 品質チェック → 研究用ファクター計算 → AI によるニュースセンチメント判定 → 監査ログ/発注までを想定したモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フォールトトレラントな外部 API 呼び出し」「テストしやすい実装（依存注入や差替え可能な内部関数）」です。

---

## 特徴（機能一覧）

- データプラットフォーム（data）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 日次 ETL パイプライン（株価 / 財務 / カレンダーの差分取得と保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキングパラメータ除去・正規化）
  - 監査ログスキーマ（signal / order_request / executions テーブル）と初期化ユーティリティ

- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）などの評価ユーティリティ
  - Zスコア正規化ユーティリティ

- AI（ai）
  - ニュース NLP（gpt-4o-mini を用いた銘柄毎のセンチメント算出）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）

- 設定管理（config）
  - .env / .env.local の自動読み込み（プロジェクトルート判定: .git または pyproject.toml）
  - 環境変数ラッパー（settings）で型安全にアクセス

- その他設計上の配慮
  - DuckDB を想定した SQL ベースの処理（ETL / 保存は冪等）
  - OpenAI / J-Quants API 呼び出しに対する堅牢なリトライ・バックオフ
  - テストしやすさのため内部呼び出しを差し替え可能

---

## 前提・依存関係

- Python 3.10+
- 推奨ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS 源）
- 環境変数に API トークン等を設定すること（下記参照）

requirements.txt を用意している場合はそちらに従ってください。最小限で動かす例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - プロジェクトルートに `pyproject.toml` あるいは `.git` が存在することを想定（.env 自動読み込みの対象判定に利用）。

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -e .   （パッケージを開発モードでインストール）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（README 用の例）
     - JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY（AI 機能利用時に必須）: OpenAI API キー
     - KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
     - KABU_API_BASE_URL（任意, デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意）: LINE 通知用
     - DUCKDB_PATH（任意, デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（任意, 監視 DB 用デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（任意, デフォルト "instant"。有効値: instant|partial|never|reject）
     - KABUSYS_ENV（任意, デフォルト "development"。有効値: development|paper_trading|live）
     - LOG_LEVEL（任意, デフォルト "INFO"）

   - .env の自動パースはシンプルなシェル形式（export KEY=val / KEY=val, クォート対応、コメント対応）をサポートします。

5. データディレクトリの準備（必要に応じて）
   - デフォルトでは `data/` に DuckDB ファイルや監視用 SQLite を保存します。環境変数で上書き可能です。

---

## 使い方（簡易ガイド）

以下は代表的な Python API の利用例です。実行するスクリプトはプロジェクト内に作成してください。

- 設定参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などでアクセス可能

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースセンチメントの算出（ai）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key="<OPENAI_API_KEY>")
  - print(f"書き込み銘柄数: {n}")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="<OPENAI_API_KEY>")

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- J-Quants API の直接利用
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()
  - records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,31))

注意点:
- AI 呼び出し（score_news, score_regime）は OpenAI API キーが必要です。関数は api_key 引数でキー注入可能（テスト用に差替えしやすい）。
- 日付処理は内部で明示的に target_date を受け取り、datetime.today()/date.today() 参照を避けているため、バックテスト・再現性に配慮しています（ルックアヘッドバイアス防止）。
- ETL/保存処理は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）に設計されています。

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - settings: アプリ設定（環境変数ラッパー）。自動で .env/.env.local を読み込む挙動あり。

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ含む）
  - pipeline: ETL 処理のエントリポイント（run_daily_etl 等）
  - quality: データ品質チェック
  - news_collector: RSS 収集と前処理
  - calendar_management: 市場カレンダー管理（営業日判定等）
  - audit: 監査ログスキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp: ニュースを LLM で処理し ai_scores に書き込む（score_news）
  - regime_detector: マクロ + MA200 を合成して market_regime を計算（score_regime）

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成（主なファイル）

プロジェクト内の主要なソース配置（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (他の研究用モジュール)
    - research/__init__.py
    - ai/__init__.py

（上は本リポジトリに含まれるモジュールの主要な一覧です。詳細はソースコードを参照してください）

---

## 運用上の注意

- .env の自動ロードはプロジェクトルート（.git か pyproject.toml を探索）を基準に行います。テストなどでこの自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の API 呼び出しは外部サービスのレート制限や課金に依存します。運用時はトークン管理・コスト管理に注意してください。
- Paper Trading 機能を使う場合、settings.paper_fill_mode（instant/partial/never/reject）で挙動を変更できます。
- DuckDB のバージョン差異（executemany の空リスト等）をコード内で考慮していますが、実行環境の DuckDB バージョンによっては挙動が異なる可能性があります。

---

## 開発・貢献

- コードの修正・拡張は PR ベースで行ってください。ユニットテストと簡単な統合テストを追加していただけると助かります。
- 外部 API 呼び出し箇所は差し替え可能に実装しているため、モックを使ったテストが容易です（例: unittest.mock.patch で内部の _call_openai_api 等を差替え）。

---

必要であれば、README にサンプル .env.example、より詳細な CLI/サービス起動手順、またはユースケース別のチュートリアル（ETL→AI→トレードフロー）を追記します。どの追加情報が欲しいか教えてください。