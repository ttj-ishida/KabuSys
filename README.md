# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ（KabuSys）の README です。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）等を含むモジュール群で構成されています。

## プロジェクト概要
KabuSys は日本株運用のための内部ツール群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータ永続化（raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース記事の収集・NLP による銘柄センチメント算出（OpenAI 使用）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 取引監査ログ（signal → order_request → execution のトレース用スキーマ）

設計上の注意点として、バックテスト時のルックアヘッドバイアス対策（target_date の明示的使用）や API リトライ／フェイルセーフの実装が意識されています。

---

## 機能一覧
- data:
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証・リトライ・レート制御）
  - pipeline: 日次 ETL 実行（差分取得 + 品質チェック）
  - calendar_management: 市場カレンダー管理・営業日ロジック
  - news_collector: RSS からのニュース収集（SSRF 対策・前処理）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（シグナル・発注・約定）スキーマ初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Z スコア正規化等）
- ai:
  - news_nlp.score_news: ニュースを元に銘柄ごとの ai_score を生成して ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF とマクロニュースを使って市場レジームを判定し market_regime テーブルへ書込
- research:
  - factor_research: モメンタム/バリュー/ボラティリティなどのファクター計算
  - feature_exploration: 将来リターン計算、IC、ファクター統計等
- config: 環境変数 / .env 読み込み、Settings オブジェクトによる設定管理

---

## セットアップ手順

前提: Python 3.10+（typing の union | を利用）を想定しています。

1. 仮想環境を作成・有効化（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（最低限の主要依存）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際の用途に応じて追加パッケージが必要になる可能性があります（例: tests 用ライブラリ等）。

3. リポジトリを開発モードでインストール（任意）
   ```
   pip install -e .
   ```
   （pyproject.toml / setup.cfg が存在する場合はそちらを使ったインストールが可能です）

4. 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（モジュール kabusys.config が自動読み込みを行います）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション等のパスワード（必要な場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知連携に使う場合
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と例）

基本的に各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- 設定・接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores への書込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written codes: {written}")
  ```

- 市場レジーム判定（market_regime への書込み）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化
  - 既存の DuckDB 接続へテーブルを追加する:
    ```python
    from kabusys.data.audit import init_audit_schema

    init_audit_schema(conn, transactional=True)
    ```
  - 監査ログ専用の新しい DB を初期化して接続を取得する:
    ```python
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    ```

- 研究用ファクター計算の呼び出し例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出すため API キーが必要です。テスト環境ではこれらの内部の HTTP 呼び出しをモック（patch）して使う設計になっています。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を前提に実装されています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env のパースと Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS 収集
    - quality.py             — 品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計関数
  - monitoring/               — （監視・実行制御関連モジュールが入る想定）
  - execution/                — （発注実行関連モジュールが入る想定）
  - strategy/                 — （戦略定義関連モジュールが入る想定）

---

## 補足 / 実運用上の注意
- 環境管理:
  - .env 自動ロードはプロジェクトルートを基準（.git または pyproject.toml を探索）に行われます。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - retry/backoff 処理や JSON モードの扱い（厳密な JSON を期待）といった考慮が実装されていますが、API 仕様の変更には注意してください。
- J-Quants:
  - トークンは refresh トークン → id token を経由して取得します。get_id_token や _request は 401 リフレッシュや retry を実装しています。
- テスト:
  - 外部 API を呼ぶ箇所（OpenAI、J-Quants、RSS fetch など）はモックして単体テストを書くことを推奨します（既に各モジュールに差し替え可能な内部関数設計があります）。

---

問題・要望・補足したい点があれば、どの部分について詳しく README に追加すべきか教えてください。必要であれば .env.example の完全テンプレートや起動スクリプト例（systemd / supervisor 用）も追記できます。