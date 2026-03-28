# KabuSys

日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
主に以下を提供します：J-Quants からのデータ ETL、ニュース収集・NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレース）など。

---

## 概要

KabuSys は日本株の自動売買システムを構成するコア機能群をモジュール化した Python パッケージです。  
主な目的は次のとおりです。

- J-Quants API を使った差分 ETL（株価 / 財務 / カレンダー）
- RSS ベースのニュース収集と LLM（OpenAI）を用いた銘柄別センチメントスコア化
- ETF とマクロニュースを合成したマーケットレジーム判定
- 研究（ファクター計算・将来リターン・IC 計算 等）
- 監査ログ（signal → order_request → execution のトレース可能なテーブル群）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存ロジック）
  - market_calendar 管理（営業日判定・next/prev）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: 銘柄ごとのニュースを LLM でスコア化して ai_scores に書き込む（batch / JSON mode / retry）
  - regime_detector: ETF (1321) の MA とマクロニュース LLM を合成して market_regime テーブルへ書き込む
- research/
  - factor_research: momentum / value / volatility / liquidity 等の計算
  - feature_exploration: 将来リターン計算、IC、factor_summary、rank
- config: 環境変数自動ロード（.env / .env.local）と settings オブジェクト

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（例）。

   requirements.txt が無ければ少なくとも以下をインストールしてください：

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは追加の依存関係（ログ環境、テストツール等）がある場合があります。

3. 開発用にパッケージをインストール（editable）：

   ```bash
   pip install -e .
   ```

4. 環境変数を設定します。プロジェクトルートに `.env` を配置すると、config モジュールが自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須と思われる環境変数（少なくとも以下を設定してください）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（使用する場合）
   - SLACK_BOT_TOKEN       : Slack 通知に必要
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - OPENAI_API_KEY        : OpenAI 呼び出し時に使用（関数引数で渡すことも可能）
   
   オプション（デフォルトあり）：
   - DUCKDB_PATH           : duckdb ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（監視用）パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG/INFO/...（デフォルト INFO）

---

## 使い方（基本例）

以下は典型的なワークフロー例です（Python API を直接呼ぶパターン）。

1. 設定と DB 接続

   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行

   run_daily_etl によって calendar → prices → financials を差分で取得し、品質チェックまで行います。

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. ニュース NLP（銘柄ごとのスコア化）

   OpenAI API キーは env にある場合は省略可能。target_date はスコア対象日（前日15:00JST～当日08:30JST のウィンドウ）。

   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> env の OPENAI_API_KEY を使用
   print(f"written {written_count} scores")
   ```

4. 市場レジーム判定

   ETF 1321 の MA とマクロニュース LLM を用いて market_regime に書き込みます。

   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査ログ DB 初期化（監査専用 DB を使う場合）

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

6. 研究用関数（例: モメンタム計算）

   ```python
   from kabusys.research.factor_research import calc_momentum
   from datetime import date

   momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
   ```

注意点：
- OpenAI 呼び出しは課金対象かつ外部 API です。api_key を引数で渡すことで関数単位で制御できます（テスト時にモック可能）。
- 日付計算・DB クエリは「ルックアヘッドバイアス」を避ける設計です。関数は内部で date.today() などを無闇に参照しないことを意識しています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数読み込み & settings
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュース NLP スコアリング
    - regime_detector.py    -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント + 保存ロジック
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult の再エクスポート
    - news_collector.py     -- RSS 収集・正規化
    - calendar_management.py-- カレンダー管理（is_trading_day 等）
    - quality.py            -- データ品質チェック
    - audit.py              -- 監査ログの DDL / 初期化
    - stats.py              -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py    -- momentum / value / volatility 等
    - feature_exploration.py-- forward returns / IC / summary
  - ai, data, research の各モジュールは unit-test しやすい設計（外部呼び出しは分離・引数注入可能）

---

## 補足・運用上の注意

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API レート制限・リトライ・トークンリフレッシュは jquants_client 側で実装済みです。
- OpenAI 呼び出しはリトライやフェイルセーフ（エラー時はデフォルトスコアで継続）を組み込んでいますが、API 利用制限やコストに注意してください。
- DuckDB のバージョン差異により executemany の挙動が異なるため、パラメータの空リストなどに注意して設計されています。
- テストや CI では外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックすることを推奨します（コード内も差し替え可能な設計）。

---

必要に応じて README に実行スクリプト例（cron ジョブ、Dockerfile、systemd ユニット）や .env.example、requirements.txt、開発フロー（テスト・lint など）を追加できます。必要であればテンプレートを作成しますのでお知らせください。