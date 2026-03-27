# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（開発版）

このリポジトリは、J-Quants や RSS、OpenAI（LLM）等を用いて市場データの収集・品質チェック・特徴量生成・ニュースセンチメント評価・市場レジーム判定・監査ログ管理までをサポートする内部ライブラリ群です。DuckDB をメインの分析用 DB として想定しています。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）
- RSS ニュース収集と前処理、記事と銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメント評価（銘柄別 / マクロ）
- マーケットレジーム判定（ETF 1321 の MA とマクロニュースを合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ）および研究用統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用スキーマ初期化とユーティリティ
- 設定管理（.env 自動読み込み、環境変数取得）

設計方針として、ルックアヘッドバイアス防止、冪等性（INSERT ON CONFLICT）やフェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- 環境設定
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示と検証
- データ取得 / ETL
  - J-Quants クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - ETL パイプライン（run_daily_etl、個別 ETL）
  - 市場カレンダーの更新・営業日判定
- ニュース処理
  - RSS フィード取得（SSRF 対策、gzip/サイズ制限、トラッキングパラメータ除去）
  - ニュース前処理（URL除去・空白正規化）
  - OpenAI を用いた銘柄別ニュースセンチメント（batch）およびマクロセンチメント評価
- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化などのユーティリティ
- データ品質
  - 欠損・スパイク・重複・日付不整合チェック
  - QualityIssue 型による検査結果の一括取得
- 監査ログ
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査スキーマ初期化関数（init_audit_schema / init_audit_db）
- その他
  - DuckDB を中心に SQL を組み合わせた効率的な実装
  - OpenAI 呼び出しは応答パースやリトライを含む堅牢な実装

---

## セットアップ手順

以下はローカル開発環境での一般的な手順例です。

前提:
- Python 3.10+（型アノテーション union などを使用）
- Git

1. レポジトリをクローン
   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成と有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   - プロジェクトに付属の pyproject / requirements がない場合、次をインストールしてください（一例）:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発時は追加で linters やテストフレームワークを入れてください。

4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` や `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（少なくとも実行する機能に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（ニューススコアリング / レジーム判定で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等を使う場合）
   - SLACK_BOT_TOKEN: Slack通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意（デフォルト値あり）:
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な例）

ここでは主要なユーティリティの呼び出し例を示します。いずれも DuckDB 接続を渡して使用します。

- DuckDB 接続例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア付与（前日15:00JST〜当日08:30JST のウィンドウ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
  ```

  note: OpenAI API キーは `OPENAI_API_KEY` 環境変数、または `api_key` 引数で渡せます。

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 監査スキーマを既存接続に適用
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 銘柄ごとの dict のリストが返る
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for issue in issues:
      print(issue)
  ```

注意:
- OpenAI 呼び出しを伴う関数は API レート・リトライ・JSON バリデーションを実装していますが、API キー・ネットワークの有効性に依存します。
- ETL / jquants_client はネットワーク呼び出し・トークン刷新・レート制御を含みます。実行時は J-Quants の認証情報が必要です。

---

## ディレクトリ構成

主要なファイル・パッケージ概要:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント付与（銘柄別）
    - regime_detector.py     # マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - etl.py                 # ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py      # RSS 収集・前処理
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py             # データ品質チェック（欠損・スパイク等）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算
    - feature_exploration.py # 将来リターン・IC・統計サマリー等
  - ai/、data/、research/ といったサブパッケージで機能を分離

（上はコードベースに含まれる主要モジュール抜粋です）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI): OpenAI API キー（news_nlp, regime_detector 等で使用）
- KABU_API_PASSWORD (必須 if 使用): kabu API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development|paper_trading|live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env ファイルのパースは `kabusys.config` 内で行われ、`.git` または `pyproject.toml` のあるディレクトリをプロジェクトルートとして探索します。`.env.local` は `.env` の上書きとして読み込まれます（OS 環境変数は保護され上書きされません）。

---

## 開発上の注意 / 設計メモ

- ルックアヘッドバイアス防止のため、ほとんどの関数は内部で date.today()/datetime.today() を安易に参照せず、必ず `target_date` 等の引数で日付を明示的に受け取ります。
- DuckDB に対する INSERT は冪等化（ON CONFLICT）を意図しています。外部から DB を操作する際は注意してください。
- OpenAI 呼び出しは JSON mode を使用し、レスポンスバリデーション・リトライ・バックオフを含みます。テスト時は内部の `_call_openai_api` をモックして差し替えられる作りになっています。
- RSS 取得は SSRF 対策（リダイレクト検査・プライベートホスト拒否）や受信サイズ制限、defusedxml を利用した XML パース保護を行っています。

---

## 貢献・ライセンス

この README はコードベースの概要説明を目的としています。実際に外部システム（証券会社 API / J-Quants / OpenAI / Slack 等）と連携する場合は、各サービスの利用規約・認証情報管理・秘密情報の保護に十分注意してください。

ライセンス情報・貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README の内容で補足が必要な箇所（たとえば具体的な .env.example のテンプレートや、CI 用の設定、詳細な SQL スキーマ説明など）があれば教えてください。追加でサンプルスクリプトやユースケース別の実行手順も用意できます。