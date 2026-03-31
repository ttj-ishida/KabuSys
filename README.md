# KabuSys — 日本株自動売買システム（README）

このドキュメントはリポジトリ内の Python パッケージ `kabusys` の概要、機能、セットアップ手順、および主要な使い方を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）、リサーチ用ファクター計算など、運用に必要なコンポーネントをモジュール化して提供します。

設計上の特徴：
- Look-ahead バイアス対策（内部で date.today() を不用意に参照しない等）
- DuckDB を利用したローカルデータベース中心の処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- AI（OpenAI）呼び出しは JSON モードでの応答を期待しバリデーションを実施

---

## 主な機能一覧

- データ収集・ETL
  - J-Quants から株価日足、財務データ、上場情報、JPX カレンダーを差分取得（pagination 対応）
  - ETL の品質チェック（欠損、スパイク、重複、日付整合性）
  - ニュース収集（RSS）と記事の前処理・保存
- AI（ニュース NLP / レジーム判定）
  - ニュース記事をまとめて OpenAI に送信し、銘柄別センチメント（ai_scores）を生成
  - ETF（1321）200日MA乖離とマクロセンチメントを組み合わせた市場レジーム判定（bull/neutral/bear）
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - 発注トレーサビリティ（UUID ベースの冪等管理）
- リサーチ用ユーティリティ
  - モメンタム・ボラティリティ・バリューのファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、Zスコア正規化など
- カレンダー管理（JPX）
  - 営業日判定、次/前営業日、期間内営業日列挙、カレンダー夜間更新ジョブ等

---

## 要件（Dependencies）

主な依存パッケージ（例）：
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

適切なバージョンは環境に合わせて調整してください。

---

## インストール

開発リポジトリをクローンしてローカルで使う例：

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

4. editable インストール（開発時）
   ```
   pip install -e .
   ```

---

## 環境変数 / 設定

`kabusys.config` モジュールは自動的にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を読み込み、環境変数をセットします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数（例）：
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
- OPENAI_API_KEY         : OpenAI API キー（score_news / regime 判定で使用）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN        : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID       : Slack チャネル ID

その他（任意・デフォルトあり）：
- KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
- LOG_LEVEL (DEBUG|INFO|...) — デフォルト "INFO"
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"

例 `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要 API の例）

以下はパッケージ内関数の利用例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を渡して使います。

- DuckDB 接続の基本
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を参照
  print("scored:", n_written)
  ```

- 市場レジーム判定（ETF 1321 + マクロセンチメント）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログスキーマ初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダージョブ（J-Quants からカレンダーを取得して保存）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

注意：
- AI 系関数（score_news, score_regime）は OpenAI API を呼び出します。API 呼び出しはリトライやフォールバック（失敗時は中立スコア）を含みますが、API キーは必ず設定してください（引数で注入可能）。
- J-Quants 関連は `JQUANTS_REFRESH_TOKEN` を利用して id_token を取得します。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP / OpenAI を使った銘柄別スコアリング
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理（営業日判定等）
    - etl.py (re-export)
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — 共通統計ユーティリティ（z-score）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（テーブル定義 / 初期化）
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集と保存
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（注）上記はこの README 作成時点での主要モジュールであり、追加・変更される可能性があります。

---

## 運用上の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）は運用モード（development / paper_trading / live）で切り替えを行い、特に本番（live）ではログレベルや発注周りの安全ガードを厳格に保ってください。
- OpenAI 呼び出しはコストとレート制限に注意。バッチ化（news_nlp は銘柄チャンク単位で処理）されていますが、APIキーの使用量は監視してください。
- ETL 実行は定期バッチ（夜間）で行い、calendar_update_job を先に実行して営業日を整えてから株価 ETL を行うことを推奨します（pipeline.run_daily_etl はこの順で実行します）。
- DuckDB ファイルは定期バックアップを行ってください。監査ログは削除しない想定です。
- テスト／CI 環境では自動 .env ロードをオフにするために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

---

## 開発・テスト

- ユニットテストでは OpenAI 呼び出し等外部依存をモック（patch）して実行することを想定しています（news_nlp._call_openai_api, regime_detector._call_openai_api 等）。
- network 呼び出し（RSS / J-Quants）は外部へ実際にアクセスしないようにモックしてください。

---

## ライセンス・貢献

本リポジトリのライセンスやコントリビュート方法はリポジトリのトップレベル LICENSE / CONTRIBUTING を参照してください。

---

この README はコードベースの主要部分をカバーしています。追加の使用例や運用ガイドが必要であれば、どの機能に関して詳細を出すか指定してください。