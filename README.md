# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、および市場レジーム判定などのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムおよびリサーチ基盤向けの共通ユーティリティ群をまとめた Python パッケージです。主に以下をサポートします。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB への保存・品質チェック含む）
- RSS ベースのニュース収集と前処理（SSRF 対策、正規化、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析・市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- 取引監査ログスキーマ（シグナル → 発注 → 約定 のトレース可能なテーブル群）
- カレンダー / 営業日判定ユーティリティ、データ品質チェック

設計方針として、バックテスト時のルックアヘッドバイアスを防ぐために日付・ウィンドウ処理を明示的に扱い、外部 API 呼び出しはリトライとフェイルセーフを備えています。

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env / .env.local からの自動ロード（プロジェクトルート検出）
  - settings により重要設定をプロパティ経由で取得
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証/ページネーション/保存関数）
  - pipeline: 日次 ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理（SSRF 対策、gzip、XML セーフパース）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化
- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、銘柄ごとの ai_score を生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロ記事の LLM センチメントを合成して market_regime テーブルへ保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. 開発環境（Python 3.10 以上を推奨）を用意します。

2. リポジトリをクローンしてパッケージをインストール（編集可能モードを推奨）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"     # requirements はプロジェクトに合わせて調整
   ```

3. 必要な主な依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ：urllib, json, logging, datetime 等）

   実際の requirements.txt / pyproject.toml に合わせてインストールしてください。

4. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動で読み込まれます（詳細は下記）。
   - 必須（主に Settings で require されるもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必要な機能を使用する場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabu API を使う場合
   - 推奨 / 省略可（デフォルトあり）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env ロードを無効化
     - OPENAI_API_KEY — OpenAI を使う処理はこれを環境変数または関数引数で渡す

5. データベース
   - デフォルトの DuckDB ファイル: data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を別に作ることも可能（init_audit_db の db_path 引数で指定）

---

## 環境変数と .env の自動ロード

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、`.env`→`.env.local` の順で読み込みます。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
- .env のパースはシェル風（export プレフィックス、クォート、コメント扱い等）に対応しています。

必須 env（まとめ）
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD（kabu 関連を使う場合）
- OPENAI_API_KEY（AI 機能を使う場合）

---

## 使い方（サンプル）

以下は主要な機能を呼び出す簡単な例です。適宜ログ設定や接続先パスを変更してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants トークンは settings から利用可能）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対して AI スコアを付ける（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env または引数
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  # :memory: でインメモリ DB も可
  audit_conn = init_audit_db("data/audit_kabusys.duckdb")
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄ごとの辞書リスト
  ```

---

## よくある注意点 / 設計上のポイント

- ルックアヘッドバイアス防止
  - 多くの関数は内部で date.today() を直接参照せず、呼び出し側で target_date を渡す設計です。バックテストでは常に明示的な日付を使用してください。
- フェイルセーフ
  - OpenAI / HTTP 通信はリトライやフォールバック（ゼロスコアやスキップ）を行い、処理全体を停止させないように設計されています。
- DuckDB の executemany では空リストが問題になるバージョンがあるため、実装側で空チェックを行っています。
- news_collector は SSRF 対策、gzip 上限チェック、defusedxml による XML パースを実施します。
- jquants_client はレート制御（120 req/min）とトークン自動リフレッシュ、ページネーション対策を備えています。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 以下を抜粋）:

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research, monitoring, strategy, execution など（パッケージの公開 API に含める予定のモジュール群）
  - その他ユーティリティ（logging 設定等はプロジェクト外で管理する想定）

---

## テスト / 開発

- 各モジュールは外部依存（OpenAI クライアントやネットワーク I/O）が含まれるため、ユニットテスト時は該当呼び出しをモックしてください（コード内でモックしやすいよう設計されています）。
- news_nlp._call_openai_api や regime_detector._call_openai_api はテスト用に patch しやすくなっています。
- データベースの初期化やスキーマ作成は data.audit.init_audit_schema 等の関数を利用してください。

---

## ライセンス・貢献

（ここにはプロジェクト固有のライセンスやコントリビュートガイドラインを記載してください）

---

README は必要に応じてプロジェクト内の pyproject.toml / requirements.txt / CI 設定と合わせて更新してください。必要であれば、インストールコマンドの具体的な requirements やサンプル .env.example を追記します。