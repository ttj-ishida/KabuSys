# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL、ニュース収集・NLP、研究用ファクター計算、監査ログなどの主要機能を提供します。

主な設計方針:
- DuckDB を中心としたローカルデータレイヤ（Look‑ahead バイアスに配慮）
- J-Quants API / RSS / 証券API など外部ソースとの連携を容易にするユーティリティ群
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（フェイルセーフ設計）
- 冪等性・トランザクション・品質チェックを重視した実装

---

## 機能一覧

- 環境変数および .env 自動読み込み (kabusys.config)
  - 自動ロード: プロジェクトルートの `.env` / `.env.local` を順に読み込み
  - 必須設定の取得ヘルパー、環境 (development / paper_trading / live) 検証
- データ ETL (kabusys.data.pipeline / jquants_client)
  - J-Quants からの株価、財務、カレンダー取得（ページネーション / レート制御 / トークン自動更新）
  - DuckDB へ冪等保存（ON CONFLICT）
  - run_daily_etl による日次パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック (kabusys.data.quality)
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得、前処理、raw_news 保存（SSRF / Gzip / サイズ制限対策）
- ニュース NLP（OpenAI）(kabusys.ai.news_nlp)
  - 指定時間ウィンドウのニュースを銘柄ごとに集約し、LLM によるセンチメントを ai_scores テーブルへ書き込み
  - バッチ・リトライ・レスポンスバリデーション付き
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF(1321) の MA200 乖離 + マクロニュースセンチメントを合成して日次レジームを market_regime に保存
- 研究ユーティリティ (kabusys.research)
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC、統計サマリー
- 監査ログ（トレーサビリティ）(kabusys.data.audit)
  - signal_events / order_requests / executions など監査テーブルの初期化ユーティリティ
- 汎用統計 (kabusys.data.stats)
  - Z スコア正規化など

---

## 必要条件・依存パッケージ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, datetime, logging 等）

例（仮の requirements.txt 作成時）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／作業ディレクトリへ移動

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （パッケージ管理ファイルがあれば pip install -r requirements.txt / pip install -e .）

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（kabusys.config が起点）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

   例: .env（最低限必要なキー）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   ```

5. データベース格納先ディレクトリ作成（必要なら）
   mkdir -p data

---

## 使い方（主な API と実行例）

下記は最小限の利用例です。実行前に環境変数を設定してください。

- DuckDB 接続を開いて日次 ETL を実行する
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコアリング（ai_scores への書き込み）
  ```
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026,3,20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームスコアの算出（market_regime テーブルへ保存）
  ```
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026,3,20))
  ```

- 監査用 DuckDB を初期化する
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants の id_token を明示的に取得
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  print(token)
  ```

注意点:
- OpenAI 呼び出しには OPENAI_API_KEY（または関数引数で api_key）を必ず設定してください。
- J-Quants 関連は JQUANTS_REFRESH_TOKEN を設定しておくと run_daily_etl 等が自動でトークンを取得します。
- 関数群は「ルックアヘッドバイアス」を避ける設計のため、target_date を明示して使用することを推奨します。

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数読み込み・検証（.env 自動ロード含む）
  - settings インスタンスを通して各種設定を取得

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、DuckDB 保存ユーティリティ
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, ...）
  - news_collector: RSS 収集・前処理
  - calendar_management: 営業日判定・calendar 更新ジョブ
  - quality: データ品質チェック
  - stats: zscore_normalize 等
  - audit: 監査ログスキーマ初期化

- kabusys.ai
  - news_nlp: ニュースセンチメントスコア取得（score_news）
  - regime_detector: 市場レジーム算出（score_regime）

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - jquants_client.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - etl.py
  - audit.py
  - (その他: schema 初期化ユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- (strategy/, execution/, monitoring/ がトップパッケージ API として想定されていますが、実装はコードベースに応じて追加されます)

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

---

## トラブルシューティング

- .env が読み込まれない場合
  - プロジェクトルートは .git または pyproject.toml で検出されます。パッケージ配置状況によっては自動検出に失敗するので、必要なら明示的に環境変数を export してください。
  - 自動ロードを無効化するフラグがセットされていないか確認してください。

- OpenAI / J-Quants API 呼び出し失敗
  - API キー／トークンが正しいか、ネットワーク接続、レート制限に達していないかを確認してください。
  - LLM 呼び出しはリトライ・フォールバック（スコア=0）を実装していますが、大規模障害時はログを参照してください。

- DuckDB の書き込みエラー
  - スキーマが未作成の場合は該当 DDL を実行してテーブルを作成してください（kabusys.data.audit.init_audit_schema 等）。
  - executemany に空リストを渡すとエラーになるバージョン差があるため、ライブラリ内で防止措置が取られています。

---

## 開発・テストメモ

- テスト時に .env の自動読み込みを無効化する:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク関連はモック可能な設計（関数単位で差し替えられるように実装されています）。
- 各モジュールは look‑ahead バイアスを避けるため、明示的な target_date に依存する実装になっています。バックテストやシミュレーションでは必ず date を指定してください。

---

もし README に追記したい実行コマンド例や CI 設定、あるいは不足している利用例があれば教えてください。必要に応じてサンプル .env.example や Docker / systemd 用の起動手順なども作成します。