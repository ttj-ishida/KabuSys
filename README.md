# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュース収集・LLM によるセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよび研究プラットフォーム向けのユーティリティ群です。主な設計方針は以下の通りです。

- Look-ahead bias を排除する（内部で date.today()/datetime.today() を直接参照しない設計のモジュールが多い）
- DuckDB をデータストアとして採用し、ETL は冪等（ON CONFLICT / INSERT/UPDATE）で安全に実行
- J-Quants API のレート制御・リトライを内蔵
- ニュースは RSS から収集し、OpenAI（gpt-4o-mini 等）の JSON モードでバッチ評価
- 監査ログでシグナルから注文・約定までのトレーサビリティを確保

---

## 主な機能一覧

- データ ETL
  - J-Quants からの株価（日足）取得（差分 / ページネーション対応）
  - 財務データ・上場銘柄情報・JPX カレンダーの取得
  - DuckDB への冪等保存（save_* 関数）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（quality モジュール）
- マーケットカレンダー管理
  - 営業日判定 / 次営業日 / 前営業日 / 期間内営業日の取得
  - calendar_update_job による夜間更新
- ニュース収集・NLP（AI）
  - RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - ニュースごとの銘柄センチメントスコアを OpenAI で生成（news_nlp.score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を組合せた市場レジーム判定（regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC 計算・統計サマリ・Z スコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化
  - init_audit_schema / init_audit_db により監査 DB 初期化
- 設定管理
  - 環境変数および .env/.env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定取得

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションの union 構文を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 主要依存の例:
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリで賄えるものが多いです

4. 必要な環境変数を設定（.env をルートに置く）
   パッケージはプロジェクトルート（.git または pyproject.toml の親）を検出して `.env` / `.env.local` を自動ロードします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限必要な環境変数（使用する機能により追加で必要になる場合があります）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先
   - OPENAI_API_KEY: OpenAI を利用する場合
   - DUCKDB_PATH: (任意) デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: (任意) 監視用 SQLite データベースパス

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はライブラリ API の簡単な使用例です。DuckDB の接続オブジェクト（duckdb.connect）を渡して操作します。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）でスコアを生成する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定済みなら api_key 引数は省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {n_written}")
  ```

- 市場レジームスコアを計算して書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "records")
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring.db")
  # conn は duckdb 接続。監査用テーブルが作成される
  ```

---

## 設定管理について

- settings オブジェクトを通じて設定値を参照できます:
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.is_live)
  ```
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` 上書き可能。
  - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys パッケージ配下に実装があります。概観:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news）
    - regime_detector.py      — ETF MA200 とマクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント（fetch_* / save_*）
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — マーケットカレンダー管理
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査テーブル定義・初期化
    - etl.py                  — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター（momentum / volatility / value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
  - research/（その他）...
  - (strategy/, execution/, monitoring/ などは __all__ に含まれているが実装が追加される想定)

---

## 注意事項 / 運用上のポイント

- OpenAI や J-Quants の API キーは機密情報です。`.env` を Git 管理しないようにしてください。
- OpenAI 呼び出しは JSON モードを前提にし、レスポンスのバリデーションを行っていますが、ネットワークやモデルの応答に対するフォールバック（0.0 やスキップ）処理が組み込まれています。
- DuckDB の executemany に関するバージョン依存の扱い（空リスト不可等）を考慮しています。DuckDB のバージョンによって挙動が変わる可能性があるので、CI で対象バージョンを固定してください。
- ETL は部分失敗（あるデータのみ取得失敗）でも他データの保全を優先するよう設計されています。run_daily_etl の戻り値（ETLResult）をログ・監査に利用してください。
- news_collector は SSRF 対策（プライベートアドレス拒否・リダイレクト検査）と XML 脆弱性対策（defusedxml）を実装しています。

---

## 開発 / テスト

- テストでは OpenAI / HTTP 呼び出しをモックすることを推奨します。モジュール内部の _call_openai_api や _urlopen などを unittest.mock.patch で差し替えられるよう設計されています。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでテスト時の自動 .env ロードを無効化できます。

---

## 参考 / 連絡

不具合や機能追加リクエストがあれば Issue を立ててください。README の内容は実装の更新に合わせて随時更新してください。

--- 

（必要に応じて README にインストール用 requirements.txt、具体的な例スクリプト、CI 設定の追加を推奨します。）