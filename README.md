# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL、ニュース収集・AIセンチメント評価、ファクター計算、監査ログ（発注トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ基盤とリサーチ／自動売買の基礎機能をまとめた Python パッケージです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・市場カレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集、前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score）およびマクロセンチメントによる市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）を格納する監査 DB 初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない）、フェイルセーフ、冪等性（DB書き込み）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存関数）
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、重複排除）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付整合性）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal/order_requests/executions）DDL・初期化
  - stats: 汎用統計ユーティリティ（z-score 正規化等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースをまとめて LLM に投げ ai_scores を生成
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime を判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- config: 環境変数・設定管理（.env 自動読み込み、必須キーの検証）

---

## 必要環境（参考）

- Python 3.10+
- 必要ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, logging, datetime など多数使用

（実際の運用では追加の依存がある場合があります。pip install 時に requirements を参照してください。ここではコード内で import されている主要パッケージを列挙しています。）

---

## 環境変数（主要）

以下は本プロジェクトで参照される主要な環境変数です（Settings クラス参照）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知に使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を使う場合）

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

LLM 用:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の引数に渡すことも可能）

自動 .env ロード:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、.env → .env.local の順で環境変数を読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: Settings にある必須キーが未設定の場合は ValueError が発生します。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

   - 実運用では requirements.txt / pyproject.toml に従ってインストールしてください。

4. パッケージをインストール（編集可能な開発モード）
   ```
   pip install -e .
   ```

5. .env を用意
   - プロジェクトルートに .env（または .env.local）を作成し、必須環境変数を設定してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（代表的な API 呼び出し例）

以下は Python REPL / スクリプトから直接使う例です。date 型は datetime.date を使います。

- DuckDB に接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（ai.news_nlp.score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  # OPENAI_API_KEY を環境変数に設定するか、第3引数に api_key を渡せます
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査 DB の初期化（監査専用 DB 作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- score_news / score_regime は OpenAI API キーが必要です（OPENAI_API_KEY または api_key 引数）。
- jquants_client の fetch 系は J-Quants の認証トークンが必要です（JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  -- 環境変数設定読み込みと Settings
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py          -- J-Quants API クライアント / 保存関数
      - pipeline.py               -- ETL パイプライン（run_daily_etl など）
      - etl.py                    -- ETLResult エクスポート
      - news_collector.py         -- RSS 収集・前処理
      - calendar_management.py    -- 市場カレンダー・営業日ユーティリティ
      - quality.py                -- データ品質チェック
      - stats.py                  -- zscore 等の統計ユーティリティ
      - audit.py                  -- 監査ログ DDL / init_audit_db
    - research/
      - __init__.py
      - factor_research.py        -- モメンタム/バリュー/ボラティリティ
      - feature_exploration.py    -- 将来リターン / IC / summary
    - research/ (公開 API 用 __all__ の管理あり)
- pyproject.toml / setup.cfg 等（プロジェクトルート）

---

## 運用上の注意・トラブルシューティング

- 環境変数不足
  - Settings の必須キー（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）が未設定だと ValueError になります。
- DuckDB ファイルパス
  - settings.duckdb_path の親ディレクトリが存在しない場合、自動で作成される処理を一部の関数で行っていますが、権限等で失敗する場合があります。パスと権限を確認してください。
- API レート制限
  - J-Quants は 120 req/min のレート制限に対応するため内部でスロットリングを行います。OpenAI 呼び出しはモデルに依存するレート/コストがあるため注意してください。
- News Collector のセキュリティ
  - fetch_rss には SSRF 対策（リダイレクト検査、プライベート IP ブロック）やレスポンスサイズ制限が実装されています。外部 RSS を追加する際は URL の妥当性を確認してください。
- ロギング
  - LOG_LEVEL 環境変数でログレベルを変更できます（INFO デフォルト）。

---

## 開発・貢献

- 単体テスト、静的解析、CI 設定などを整備していくことを推奨します。  
- 変更を加える場合はルックアヘッドバイアスや冪等性に注意してください（ETL / リサーチコードの設計方針に沿っているかを確認すること）。

---

本 README はコードベースの主要機能と利用方法をまとめたものです。具体的な運用手順や追加の依存関係、デプロイ手順はプロジェクトの運用ポリシーに合わせて追記してください。質問やサンプル実行スニペットが必要であればお知らせください。