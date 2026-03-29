# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買／データ基盤モジュール群を提供します。データ取得（J-Quants）、ETL、データ品質チェック、研究用ファクター計算、ニュースNLP（OpenAI）を用いたセンチメント解析、監査ログ（発注 → 約定のトレーサビリティ）などの機能を備えています。

主な目的は「バックテスト／リサーチ環境」と「実運用（発注・監視）」の両方をサポートすることです。モジュールは DuckDB をデータ層として前提にしています。

---

## 機能一覧

- 環境変数・設定管理
  - .env 自動読み込み（プロジェクトルート検出）と保護された上書きルール
  - 必須設定のチェック（例: JQUANTS_REFRESH_TOKEN 等）
- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
  - 日次 ETL パイプライン（市場カレンダー、日足、財務）
  - 市場カレンダーの更新・営業日判定ユーティリティ
  - ニュース RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック
  - QualityIssue 型で検出結果を返却（error / warning）
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - クロスセクション Z スコア正規化
- AI（OpenAI）連携
  - ニュースの銘柄別センチメント集計（gpt-4o-mini / JSON mode）
  - 市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 とマクロニュースを統合）
  - API エラー時のリトライ／フェイルセーフ設計
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 発注トレーサビリティ（UUID による連鎖）
- その他ユーティリティ
  - 統計ユーティリティ（zscore 正規化等）
  - 設定・ログレベル判定

---

## 必要条件（推奨）

- Python 3.10 以上（コードでの型注釈に | 記法を使用）
- DuckDB
- openai Python SDK（OpenAI クライアントを利用）
- defusedxml
- （ネットワークアクセス可能であれば）外部 API（J-Quants、OpenAI）

推奨インストールパッケージ（requirements.txt 例）
- duckdb
- openai
- defusedxml

（プロジェクト内に requirements.txt は含まれていないため、実行環境に合わせて適宜作成してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   例: pip を使う場合
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数（.env）を準備
   プロジェクトルート（.git または pyproject.toml の上位）を基準に自動で `.env` / `.env.local` が読み込まれます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定が必要な環境変数（Settings にて必須扱い）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL     : kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB のデータベースパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite 等（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / regime_detector 呼び出し時に利用）

5. データベース初期化（監査ログ等）
   監査ログ専用 DB を作る例:
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb 接続オブジェクト
   ```

---

## 使い方（主な API 使用例）

以下はライブラリをコードから利用する際の代表例です。

- 日次 ETL を実行する
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に保存する
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数にセットするか api_key 引数を渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {n_written}")
  ```

  注意: OpenAI への呼び出しは課金が発生するため、テスト時はモック推奨（コード内でも unittest.mock.patch を想定した差し替えポイントあり）。

- 市場レジームを評価して market_regime に書き込む
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマを初期化（既存 DB に追加）
  ```py
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```py
  from kabusys.research import calc_momentum
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄ごとの辞書リスト
  ```

---

## 注意点 / 運用上のポイント

- Look-ahead バイアス防止
  - 多くのモジュール（news_nlp, regime_detector, ETL 等）は内部で date.today() を参照せず、外部から target_date を渡す設計になっています。バックテスト時は必ず過去データのみを参照するようにしてください。
- OpenAI 呼び出しのモック
  - テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch してネットワーク呼び出しを防いでください（コード内に差し替えを想定したコメントがあります）。
- 自動 .env ロード
  - デフォルトでプロジェクトルートの `.env` / `.env.local` をロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB 書き込みは冪等設計
  - save_* 関数は ON CONFLICT DO UPDATE を使用して冪等にデータを保存します。ただし、外部から DB を改変した場合の挙動には注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースセンチメント解析（OpenAI）
    - regime_detector.py    -- マクロ + MA200 を用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得 + 保存）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult を再エクスポート
    - calendar_management.py-- 市場カレンダー管理（営業日判定等）
    - news_collector.py     -- RSS ニュース収集（SSRF 対策・正規化）
    - quality.py            -- データ品質チェック（欠損・重複・スパイク等）
    - stats.py              -- 統計ユーティリティ（zscore 等）
    - audit.py              -- 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    -- モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py-- 将来リターン・IC・統計サマリー等
  - ai/, data/, research/ の __init__ は公開 API を整備しています

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 開発 / テストのヒント

- OpenAI 呼び出しはネットワークと課金を伴うためユニットテストでは差し替えてください。
  - news_nlp や regime_detector 内で _call_openai_api を patch することで応答を模擬できます。
- DuckDB はインメモリでのテストが容易です（db_path=":memory:" を使用）。
  - audit.init_audit_db(":memory:") などでスキーマ初期化と単体テストが可能です。
- ロギングを INFO → DEBUG に下げると内部の実行ログが詳しくなります（LOG_LEVEL 環境変数）。

---

必要な追加情報（例: 実際の requirements.txt、.env.example、API レート制御の詳細、運用手順書等）を README に追記することができます。必要であればそれらを生成して提供します。