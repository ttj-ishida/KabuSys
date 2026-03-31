# KabuSys

日本株向けのデータプラットフォーム兼リサーチ / 自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算・特徴量探索、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- DuckDB を中心に効率的な SQL / ウィンドウ関数による処理
- 外部 API 呼び出しはフェイルセーフ（リトライ・フォールバック）を実装
- 冪等性（ETL / 保存処理は ON CONFLICT DO UPDATE 等で上書き）を重視

---

## 機能一覧

- data（ETL / Data Platform）
  - ETL パイプライン: 日次 ETL（株価、財務、カレンダー取得） — run_daily_etl
  - J-Quants クライアント（認証 / ページネーション / レート制御 / 保存関数）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、正規化、SSRF/サイズ保護）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions のスキーマ初期化・DB 初期化）
  - 汎用統計（Zスコア正規化 等）
- ai
  - news_nlp: ニュース記事群を LLM（gpt-4o-mini など）へ投げて銘柄ごとのセンチメント（ai_scores）を算出・保存
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を算出・保存
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ等

---

## 必要条件

- Python 3.10 以上（PEP 604 の `|` 型記法などを使用）
- 主な Python 依存ライブラリ（プロジェクトに requirements.txt がない場合は最低限下記を導入）
  - duckdb
  - openai
  - defusedxml

（実運用では更にロギングや Slack 通知用のライブラリなどが必要になる可能性があります）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - もし requirements.txt があれば:
     ```bash
     pip install -r requirements.txt
     ```
   - または最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` や `.env.local` を置くと自動で読み込まれます（デフォルトで自動ロードが有効）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime を実行する際に必須）
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（使用する場合）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合に必要
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル
   - 任意・デフォルト値があるもの:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db

   .env の書式は通常の KEY=VALUE をサポートし、export KEY=val 形式やシングル/ダブルクォート、インラインコメント等に対応しています。

---

## 使い方（主要なワークフロー例）

以下はライブラリ機能を直接 import して使う例です。実運用ではスクリプトや cron / Airflow 等に組み込んでください。

- DuckDB 接続作成の基本
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を明示的に渡すか、OPENAI_API_KEY 環境変数を設定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを評価して market_regime テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 監視 / 品質チェックを単体で実行
  ```python
  from datetime import date
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点
- OpenAI 呼び出しは API レートやコストに注意して利用してください。score_news / score_regime は空記事時や API 失敗時のフォールバックを持ちますが、適切なレート制御やエラーハンドリングを行ってください。
- J-Quants API についてはリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。J-Quants 側のレート制限を厳守するために内部に RateLimiter が実装されています。

---

## 主要モジュール説明（ディレクトリ構成）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主要なファイルと概要:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み（.env, .env.local を自動ロード）、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を銘柄ごとに集約して OpenAI に投げ、ai_scores を更新する
    - regime_detector.py
      - ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、ページネーション、保存関数）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL ロジック
      - ETLResult データクラス
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得、正規化、SSRF 対策、raw_news 挿入ロジック
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL と初期化関数
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、rank 等

（上記は主要ファイルの抜粋です。詳細は該当ソースコードの docstring を参照してください。）

---

## 運用上の留意点

- 環境（KABUSYS_ENV）を `live` にする場合は特に API キーや発注処理へのアクセス権・ログ保存・冪等性に注意してください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない想定で設計されています。
- ニュース収集・LLM 呼び出しはコスト・レイテンシ・プライバシーの観点でポリシーを決めてから本番導入してください。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用するか、score_news / score_regime 内で渡せる api_key 引数を用いて外部依存を注入してください。

---

必要であれば、README に以下も追記できます
- リファレンス（関数一覧と引数の詳細）
- 実行スクリプト例（cron / systemd / Docker Compose での運用例）
- CI / テストの実行方法
- 開発者向け貢献ガイド

追加で欲しいセクションがあれば教えてください。