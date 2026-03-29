# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ、監視・レジーム判定などのユーティリティを提供します。

主な設計方針として、バックテストにおけるルックアヘッドバイアスを防ぐ実装（日時参照の制限、取得ウィンドウ制御）、API 呼び出しの堅牢化（レートリミット・リトライ）、および DuckDB を用いた冪等保存を採用しています。

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- データ取得（J‑Quants 統合クライアント）
  - 日次株価（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - リクエストのレート制御・リトライ・トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリポイント
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、gzip 限度、XML 安全パーサ）
  - raw_news への冪等保存と銘柄紐付け処理を想定
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント算出（OpenAI gpt-4o-mini で JSON Mode）
  - マクロニュースを使用した市場レジーム判定（ETF 1321 の MA200 と LLM スコアを合成）
  - API 呼び出しのリトライ・フェイルセーフ（失敗時は中立スコア）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル → 発注リクエスト → 約定 のトレーサビリティ用テーブル定義と初期化ユーティリティ
  - DuckDB ベースで冪等にテーブル作成
- カレンダー管理
  - 営業日判定、next/prev 営業日取得、calendar の夜間更新ジョブ

---

## 必要な環境変数

（主要なもの）

- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 呼び出し時に使用）
- DUCKDB_PATH : デフォルト DB ファイルパス（省略可、data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB 等に使う SQLite パス（省略可、data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...、デフォルト INFO）

注意:
- パッケージ読み込み時にプロジェクトルート（.git or pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. リポジトリをクローンして開発環境にインストール（編集可能インストール）:
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

3. 依存パッケージのインストール（例）:
   ```
   pip install duckdb openai defusedxml
   ```
   - 実行環境に応じて追加ライブラリが必要になる場合があります（ネットワークアクセスや HTTP 関連など）。

4. 環境変数を設定:
   - プロジェクトルートに `.env` を置くか、環境変数を直接セットしてください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB の初期スキーマや監査 DB を作成する場合:
   - 監査ログ用 DB 初期化例（Python）:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")
     # もしくは既存の duckdb.connect() を渡して init_audit_schema(conn)
     ```

---

## 使い方（簡単な例）

以下は主要な機能を呼ぶ際の簡単なサンプルコードです。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- 日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアする（OpenAI API キーは環境変数か api_key 引数で指定）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {n} codes")
  ```

- 市場レジーム判定を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査スキーマを初期化する:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J‑Quants API を直接呼んで株価を取得する:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  # get_id_token() は settings.jquants_refresh_token を使用して id_token を返す
  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

注意点:
- AI 系関数（score_news / score_regime）は OpenAI の JSON Mode を使用します。API レスポンスの妥当性チェック・リトライを行いますが、キーが設定されていないと ValueError を発生させます。
- 各処理はルックアヘッドバイアス防止のため基本的に target_date のみを参照し、内部で date.today() を無暗に参照しない設計になっています（ドキュメント内に明記）。

---

## ディレクトリ構成 (主要ファイル)

パッケージルート: src/kabusys

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
  - etl.py (ETLResult re-export)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (他：news_collector など)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (コードベースに含まれる想定モジュールがあればここに)
- execution/, strategy/ 等（パッケージ __all__ に委ねられているが、今回の抜粋にないモジュールが存在する可能性があります）

（上記はリポジトリの抜粋に基づく主要ファイル一覧です。詳細はソースツリーを参照してください。）

---

## 開発のヒント / 注意事項

- .env 自動読み込み:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を順に読み込みます。
  - テスト時や特別なケースでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを回避できます。
- OpenAI 呼び出し:
  - gpt-4o-mini の JSON Mode を用いて厳密な JSON を期待しますが、LLM 側の応答が不正な場合に備えてパーシングのフォールバックや安全な失敗処理（スコアを 0 にフォールバック）を行っています。
- DuckDB との互換性:
  - 一部の executemany 空リストバインドや ANY(?) 形式は DuckDB バージョン差異で動作が異なるため、互換性確保のために個別ループや executemany 対策が入っています。
- セキュリティ:
  - RSS 取得では SSRF 対策、gzip サイズチェック、defusedxml を使ったパース保護を行っています。
  - J‑Quants クライアントはレート制御とトークン自動リフレッシュを実装しています。
- 設計上の保証:
  - 多くのモジュールは「失敗してもシステム全体を停止させない」フェイルセーフ挙動を採用しています（ログ出力・一部スキップ・中立値フォールバックなど）。

---

## ライセンス / 貢献

（このリポジトリにライセンスファイルがある場合はそれを参照してください。貢献ガイドライン・CONTRIBUTING.md があればその指示に従ってください。）

---

README に書かれている主な API や挙動はソースに実装されています。利用や拡張の際は該当モジュール（特に data.jquants_client, data.pipeline, ai.news_nlp, ai.regime_detector, research.*）の docstring を参照してください。必要であれば、サンプルユースケースや CLI の追加ドキュメント作成を支援します。