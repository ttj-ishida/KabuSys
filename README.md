# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI 経由）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー／約定トレース）等の機能を提供します。

主に社内バッチ処理や研究（リサーチ）環境、発注システムの内部モジュールとして利用する想定です。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数管理
  - .env / .env.local ファイル自動読み込み（プロジェクトルート検出、OS 環境変数優先）
  - 必須値は Settings クラス経由で取得（未設定時に ValueError）

- データ取得・ETL（jquants_client + pipeline）
  - J-Quants API から株価日足、財務、上場銘柄情報、JPX カレンダーを差分取得
  - Rate limiting / リトライ / トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT 相当の処理）

- ニュース収集・前処理（news_collector）
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定

- ニュース NLP（OpenAI 使用）
  - 銘柄ごとにニュースをまとめて gpt-4o-mini に投げ、センチメント（-1〜1）を ai_scores テーブルへ保存する処理（score_news）
  - OpenAI API エラー時はフェイルセーフでスキップ / 0.0 フォールバック

- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、'bull'/'neutral'/'bear' を判定（score_regime）
  - ルックアヘッドバイアス回避の設計（date パラメータを明示）

- 研究用モジュール（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Spearman）計算、ファクター要約統計
  - zscore_normalize 等の統計ユーティリティ

- データ品質チェック（quality）
  - 欠損・重複・スパイク・日付不整合などのチェックを集約（QualityIssue オブジェクト）

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル構造と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注から約定まで UUID によるトレース可能な監査設計

---

## 必要条件（想定環境）

- Python 3.10 以上（typing の | 演算子等を使用）
- 外部ライブラリ（例）
  - duckdb
  - openai（v1 SDK 想定）
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

依存はプロジェクトの setup / requirements に合わせてインストールしてください。最小手順例:

pip install duckdb openai defusedxml

またはプロジェクトルートで:

pip install -e .

---

## 環境変数（主要）

以下を設定してください（.env を推奨）。Settings クラスは .env/.env.local を自動読み込みします（プロジェクトルート検出に基づく）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能使用時）

任意（デフォルト有り/運用向け）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 をセット
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime は引数で上書き可能）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env.local が存在する場合は .env の上書きとして読み込まれます。

---

## セットアップ手順（ローカル開発向け簡易ガイド）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存インストール
   pip install -e .            # setup.py / pyproject がある想定
   または必要パッケージを個別に:
   pip install duckdb openai defusedxml

4. 環境変数を用意
   プロジェクトルートに .env を作成（上記参照）

5. DuckDB 初期化（必要に応じてスキーマを整備するスクリプトを用意してください）
   例: Python REPL で監査 DB 初期化:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な API / 実行例）

以下は Python スクリプト/REPL での呼び出し例です。いずれの関数も DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- ETL（日次パイプライン）の実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

  run_daily_etl はカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行します。エラーは ETLResult.errors に集約されます。

- ニューススコアの算出（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))  # api_key を引数で渡すことも可能
  print("wrote", written, "codes to ai_scores")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # returns 1 on success

- 監査ログスキーマの初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

- 研究用ファクター計算例
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))

---

## 主要 API の注意点 / 設計上のポイント

- ルックアヘッドバイアス回避
  - ニュース集計やレジーム判定、ETL の各処理は内部で date を明示的に扱い、datetime.today()/date.today() に依存しない設計です。バックテスト利用時のデータリーク対策が施されています。

- OpenAI 呼び出し
  - score_news / score_regime は OpenAI の JSON Mode（厳密な JSON 出力）を利用し、API エラー時はスコアを 0 にフォールバックするなどフェイルセーフ化しています。
  - テスト容易性のために内部の API 呼び出し関数をモック可能です（例: unittest.mock.patch）。

- J-Quants クライアント
  - _RateLimiter による固定間隔スロットリング（120 req/min）を実装
  - 401 時の自動トークン更新（get_id_token）とページネーション対応
  - DuckDB への保存関数は冪等（ON CONFLICT 相当）で安全に上書き保存

- ニュース収集
  - SSRF 対策、受信サイズ上限、XML の安全パーサー（defusedxml）を使用
  - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成して冪等性を確保

- 品質チェック
  - 複数チェックを実行し、重大度（error/warning）の情報を QualityIssue 型で返す。ETL は Fail-Fast ではなく問題を集約して返します。

---

## ディレクトリ構成

以下は主要ファイルの一覧（抜粋）です。実際は src/kabusys 配下にモジュールが格納されています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & 保存ロジック
    - pipeline.py             — 日次 ETL パイプライン（run_daily_etl など）
    - etl.py                  — ETLResult エクスポート
    - news_collector.py       — RSS ニュース収集
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - stats.py                — zscore_normalize 等ユーティリティ
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（監査スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

この README はコードベースに含まれる主要なモジュールと設計方針をまとめたものです。実運用時は各モジュールのドキュメントとログ出力を参照し、適切なモニタリングとリトライ戦略、権限管理を行ってください。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が設定されていない
  - settings（kabusys.config.Settings）が必須変数を参照すると未設定時に ValueError を投げます。必要な環境変数を .env または OS 環境に設定してください。

- DuckDB のパスが見つからない / ディレクトリがない
  - settings.duckdb_path の親ディレクトリを作成してください（init_audit_db は自動で親ディレクトリを作成しますが、他の処理で明示的にファイルを作る前にパスを確認してください）。

- OpenAI / J-Quants API エラー
  - ネットワーク問題やキーの期限切れなどが原因になります。ログにリトライ情報が出力されます。API キー設定を確認してください。

---

ご要望があれば、README に「開発用のセットアップ（テスト、Lint、CI）」や「運用手順（cron ジョブ / Airflow などでのスケジューリング）」の節を追加できます。どの情報を深掘りしたいか教えてください。