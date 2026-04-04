# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ KabuSys の README です。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター算出、監査ログ等のユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ／自動売買基盤向けの共通モジュール群です。主な目的は以下です。

- J-Quants API からの差分取得（株価・財務・上場銘柄・市場カレンダー）
- DuckDB を使った ETL / 永続化（冪等保存）
- RSS ベースのニュース収集と前処理／SSRF 対策
- OpenAI を使ったニュースセンチメント評価（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定（ETF とマクロセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- カレンダー管理（JPX 営業日判定、next/prev/trading days）

設計方針としては「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時のスキップ／中立化）」を重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、DuckDB 保存）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・正規化・保存ロジック（SSRF対策・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログ用テーブル定義と初期化ユーティリティ
  - stats: Zスコア正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出と ai_scores への保存
  - regime_detector.score_regime: ETF（1321）MA乖離とマクロセンチメントを合成した市場レジーム判定
- research/
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- config: 環境変数 / .env 自動読み込み、settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の構文に依存）
- Git, ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な依存ライブラリ（代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※実際の requirements はプロジェクトに合わせて管理してください。

3. 環境変数を設定
   - .env（プロジェクトルートに置く）または OS 環境変数で設定可能。自動ロード順は OS 環境 > .env.local > .env（プロジェクトルート自動検出）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注系を使う場合）
   - OPENAI_API_KEY (必須 for AI機能) — OpenAI API キー（score_news / score_regime）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意：通知用）
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - LOG_LEVEL (DEBUG/INFO/…)
   - KABUSYS_ENV (development / paper_trading / live)

4. データディレクトリを作る（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（基本例）

以下はプロジェクト内 API を直接利用する例です。ETL / AI スコアリング / レジーム判定 / 監査 DB 初期化など。

- DuckDB 接続の作成例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（None で今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）をスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を参照
  print(f"wrote {written} codes")
  ```

- 市場レジームを判定して market_regime に保存
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用の DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- AI 系（score_news, score_regime）は OpenAI API キーが必要です。api_key 引数にキーを直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN が必須です（settings.jquants_refresh_token が利用されます）。
- ETL・保存処理は冪等設計になっていますが、本番実行前にローカルでテストを推奨します。

---

## 設定（主要な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注を使う場合は必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_ENV: environment（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

config.Settings はこれら値へのアクセスラッパーを提供します（kabusys.config.settings）。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの銘柄別センチメントスコア算出（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - news_collector.py — RSS 収集・前処理・保存ユーティリティ
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査テーブル定義と初期化ユーティリティ
    - etl.py — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - research/*, ai/*, data/* には詳細な docstring と設計方針が実装済み

---

## 運用上の注意 / ベストプラクティス

- API 呼び出し（J-Quants / OpenAI）はレート・課金に注意して利用してください。
- ETL 実行は監視（ログ、監査）を組み合わせて行ってください。run_daily_etl は品質チェックを実行するオプションを持ちます。
- OpenAI の呼び出しは外部 API に依存するため、テスト時は各内部 _call_openai_api をモックしてください（モジュール内 docstring に記載）。
- DuckDB への INSERT は冪等設計（ON CONFLICT）を基本としますが、実運用ではバックアップと監査ログを必ず設定してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。

---

## 参考・開発メモ

- 各モジュールには詳しい docstring と設計方針が含まれています。実装の振る舞いやフォールバック・例外処理については各ファイルのコメントを参照してください。
- テストの際は外部 API 呼び出しやネットワーク I/O をモックすることで安定した単体テストが可能です（jquants_client._request, news_collector._urlopen, ai 内の _call_openai_api などを差し替え）。

---

問い合わせ・貢献
- バグ報告や機能追加の提案は Pull Request / Issue を通してお願いします。
- 大きな機能追加は事前に Issue で相談いただくと設計面での調整がスムーズです。

以上。必要に応じて README のセクションを追加・調整します。具体的な実行コマンドや requirements.txt を含めたい場合は、その情報を教えてください。