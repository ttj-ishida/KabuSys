# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、ファクター計算、監査ログ（DuckDB）等を含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today() / datetime.today() を直接参照しない等）
- DuckDB をデータ格納に使用し、ETL は冪等性を重視
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライ・レート制御・フェイルセーフを実装

---

## 機能一覧

- data
  - J-Quants クライアント（株価・財務・カレンダー等の取得）
  - ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、URL 正規化）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ（signal/order/execution の監査テーブル定義・初期化）
  - audit 用の DuckDB 初期化ユーティリティ
- ai
  - ニュース NLU（銘柄ごとセンチメントを OpenAI で評価 → ai_scores に書込む）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 特徴量探索・IC 計算・前方リターン計算・統計サマリー
- utils
  - 設定管理（.env の自動読み込み、環境変数ラッパー）
  - 汎用統計ユーティリティ（Z スコア正規化 等）

---

## 動作要件（例）

- Python 3.9+（型注釈により 3.10+ を想定する箇所がありますが、3.9 でも動作する実装です）
- 主要依存パッケージ（抜粋）
  - duckdb
  - openai (OpenAI の新 SDK を使用する呼び出しに準拠)
  - defusedxml
  - その他（標準ライブラリ中心）
- J-Quants API トークン、OpenAI API キーなどの外部サービス資格情報

（実際の requirements.txt / pyproject.toml はプロジェクトに合わせて作成してください）

---

## セットアップ手順

1. リポジトリをクローンして開発用にインストール（プロジェクトが src/ レイアウト）
   - pip editable install 例:
     ```
     git clone <repo-url>
     cd <repo-dir>
     pip install -e ".[dev]"  # extras がある場合
     ```
   - 依存パッケージを手動でインストールする場合:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（優先順位：OS env > .env.local > .env）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

3. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
   - OPENAI_API_KEY : OpenAI API キー（ai モジュールで使用）
   - KABU_API_PASSWORD : kabu ステーション連携パスワード（strategy/exec で想定）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知に必要
   - （オプション）KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH、KABU_API_BASE_URL

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. データベース用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要ユースケースの例）

以下はライブラリをインポートして使う基本例です。実行は各環境で適宜ラップしてください。

- 設定を参照する:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.env, settings.log_level)
  ```

- DuckDB に接続して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai.score_news）を使って銘柄ごとの AI スコアを生成:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env から OPENAI_API_KEY を参照
  print(f"Wrote scores for {written} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定等が適用されます
  ```

- 研究用ユーティリティ（ファクター計算など）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

注意点：
- OpenAI 呼び出しはエラーやレート制限に対してリトライやフェイルセーフ（スコア = 0）を行いますが、APIキーは必須です（例外を投げます）。
- ETL / 保存は冪等性を保つよう設計されています（DuckDB 側は ON CONFLICT を利用）。

---

## .env 自動読み込みの挙動

- 自動ロードはデフォルトで有効。読み込み順序（下から上に優先）：
  - OS 環境変数（最優先、上書き保護される）
  - .env.local（存在すると .env の値を上書き）
  - .env
- プロジェクトルートは `.git` または `pyproject.toml` の存在を親方向に探索して決定します。見つからない場合は自動ロードをスキップします。
- テスト等で無効化する場合：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env のパースはシェル形式（`export KEY=val` 対応、引用符・コメント処理あり）で柔軟に扱います。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に実装があります。抜粋ツリー:

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境設定 / .env ロード
    - ai/
      - __init__.py
      - news_nlp.py             -- ニュース NLU / ai_scores 書込
      - regime_detector.py      -- マーケットレジーム判定
    - data/
      - __init__.py
      - calendar_management.py  -- カレンダー管理 / 営業日判定
      - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
      - etl.py                  -- ETLResult 再エクスポート
      - jquants_client.py       -- J-Quants API クライアント / save_*/fetch_*
      - news_collector.py       -- RSS ニュース収集
      - quality.py              -- データ品質チェック
      - stats.py                -- 統計ユーティリティ（zscore_normalize）
      - audit.py                -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py      -- モメンタム / ボラティリティ / バリュー
      - feature_exploration.py  -- 将来リターン / IC / 統計サマリー
    - (他に strategy, execution, monitoring などのサブパッケージ想定)

各モジュールはドキュメント文字列で設計意図・処理フロー・フェイルセーフ等が明記されています。

---

## 開発・運用上の注意

- DuckDB の executemany に関する互換性やパラメータ空リストの扱いに注意（pipeline/news_nlp 等でガード処理があります）。
- OpenAI 呼び出しは JSON Mode を使い厳密な JSON を期待しますが、パース保険（余計な前後テキスト抽出等）を実装しています。
- J-Quants API 呼び出しはレート制御（120 req/min）・トークン自動更新を行います。ID トークンは内部キャッシュされ、必要に応じて自動でリフレッシュされます。
- 監査ログ（audit）テーブルは削除しない前提・UTC タイムスタンプで保存します。init_audit_db / init_audit_schema を使って安全に初期化してください。

---

## 参考（よく使う API）

- ETL（全体）: kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- ニューススコア: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム評価: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 監査DB初期化: kabusys.data.audit.init_audit_db(path)

---

必要があれば、README に以下を追加できます：
- 詳しいインストール手順（pyproject.toml / requirements.txt を用いた例）
- CI / テストの実行方法（pytest モック例）
- デプロイ / 運用スケジュール（ETL cron / Airflow 例）
- 実行例の Jupyter ノートブック

追加で書いてほしい内容があれば教えてください。