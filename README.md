# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダーなど、取引システム／リサーチ環境で必要となる共通処理群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けに設計されたモジュール群で、主に次の領域をカバーします。

- データ取得・ETL（J-Quants API 経由の株価・財務・カレンダー取得）
- ニュース収集と LLM を使ったニュースセンチメント（銘柄別スコアリング）
- 市場レジーム判定（ETF とマクロニュースを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を利用した永続化と効率的な SQL ベース処理

設計上の特徴:
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない）
- 冪等（idempotent）設計（DB へは ON CONFLICT 等で上書き）
- 外部 API 呼び出しに対するリトライ・バックオフ・レート制御
- テスト容易性のためキー注入／モック差替えポイントを確保

---

## 機能一覧

主な公開機能（モジュール）と役割:

- kabusys.config
  - 環境変数自動読み込み（.env / .env.local）と Settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save / id token 管理）
  - pipeline: 日次 ETL 実行（run_daily_etl）と ETL 結果クラス
  - news_collector: RSS 取得・前処理・raw_news 保存
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - regime_detector: ma200 とマクロニュースを合成した市場レジーム判定（score_regime）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ（signal / order_requests / executions）スキーマ初期化
  - stats: 汎用統計（zscore_normalize 等）
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration: 将来リターン・IC・統計サマリ等
- kabusys.ai
  - news_nlp.score_news：ニュースの LLM スコアリング
  - regime_detector.score_regime：市場レジーム判定

---

## 動作環境・依存パッケージ

最低限必要なパッケージ（例）:
- Python 3.10+
- duckdb
- openai
- defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を整備してください。）

---

## セットアップ手順

1. リポジトリをクローンする（例）
   - git clone <repo_url>
   - プロジェクトは src/ 配下にパッケージがあるレイアウトです。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   開発用にパッケージ化されている場合:
   - pip install -e .

4. 環境変数の準備
   - ルートプロジェクトに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が .git または pyproject.toml を基準に検出）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくとも開発時に必要なもの）:
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabu ステーション API パスワード（発注などを行う場合）
   - SLACK_BOT_TOKEN        — Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID       — Slack の通知先チャンネル ID
   - OPENAI_API_KEY         — OpenAI 呼び出しを行う際に使用（score_news / score_regime で参照）

   任意 / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) 既定: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
   - DUCKDB_PATH / SQLITE_PATH（データ格納パス）

   例: `.env`（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表例）

※ ここでは簡単な Python インタラクティブ／スクリプト例を示します。各関数の詳細はモジュール内ドキュメントを参照してください。

- DuckDB 接続を作る（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの LLM スコアリング（銘柄別 ai_scores へ保存）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（market_regime テーブルへ書込）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring.duckdb")
  ```

- ファクター計算 / 研究用ユーティリティ
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)

  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- データ品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

---

## .env 自動読み込みの挙動

- 起点は本モジュールのファイル位置から親ディレクトリをさかのぼり、`.git` または `pyproject.toml` が見つかったディレクトリをプロジェクトルートと見なします。
- 自動で `.env` を読み込み（OS 環境変数を上書きしない）、次に `.env.local` を上書きロードします。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys パッケージの主要モジュール構成（抜粋）

- src/
  - kabusys/
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
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (ETLResult re-export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (README に示されたがコード一覧に未展開の可能性あり)
    - execution/ (発注関連実装用の想定モジュール)
    - strategy/ (戦略関連モジュール想定)

（上記はソースに含まれる主要ファイルの一覧です。実際のリポジトリではさらに細分化されたファイルや補助モジュールが存在する可能性があります。）

---

## 注意事項 / 運用上のヒント

- OpenAI 呼び出しはレート制御・リトライロジックを持ちますが、API コストに注意してください。テスト時はキーをモックまたは短い実行で済ませてください。
- DuckDB の executemany に対する制約（空リストを渡せない等）に配慮した実装になっています。DB スキーマやバージョンと互換性を保ってください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。運用時の容量・バックアップ計画を検討してください。
- J-Quants のレート制限・認証フロー（リフレッシュ・id token）に対応したクライアント実装です。API の仕様変更に注意してください。
- 本プロジェクトは研究/実運用双方を想定しています。KABUSYS_ENV を使って環境（development / paper_trading / live）を切り替え、発注等の危険な操作は live 環境でのみ許可するポリシーを運用してください。

---

## 参考・ドキュメント参照先

- 各モジュールの docstring を参照してください（関数引数・返り値・挙動の詳細が記載されています）。
- 実際の導入時は pyproject.toml / requirements.txt を確認し、テストを含む CI 設定を行ってから運用環境へデプロイしてください。

---

ご要望があれば以下を追加できます:
- 仮想環境用の requirements.txt 例
- .env.example のテンプレート
- よくあるエラーとトラブルシューティング集
- 実際の ETL / バッチ運用スケジュール例（cron / Airflow）