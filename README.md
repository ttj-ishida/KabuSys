# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に、J-Quants API で市場データを取得し、OpenAI（gpt-4o-mini）でニュースセンチメントを評価する機能などを備えています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は次のとおりです。

- J-Quants から株価・財務・上場情報・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集・前処理・DB 保存（raw_news / news_symbols）
- ニュースを LLM に投げて銘柄別センチメント（ai_scores）を生成する NLP コンポーネント
- マクロニュースと ETF（1321）の MA200 を組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）を保持する監査テーブル初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- Look-ahead バイアスを回避する実装（関数は内部で date.today() を参照しないなど）
- API リトライやレート制御、フェイルセーフ（API 失敗時は中立スコア等で継続）を備える
- DuckDB に対する冪等保存（ON CONFLICT / executemany の扱いに配慮）

使用例（ライブラリ名空間）: `kabusys.data`, `kabusys.ai`, `kabusys.research`, `kabusys.config`

---

## 機能一覧

- ETL
  - run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl（差分取得 + 保存 + 品質チェック）
  - J-Quants クライアント（認証・ページネーション・リトライ・レート制御）
- データ管理
  - news_collector: RSS 収集 → raw_news 保存（SSRF 対策・トラッキング除去・前処理）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログテーブルの初期化（監査用 DDL / インデックス）
- AI / NLP
  - news_nlp.score_news: 指定期間のニュースをまとめて LLM で銘柄別センチメントを算出し ai_scores へ書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- 研究用
  - research.factor_research: calc_momentum / calc_value / calc_volatility
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化
- 品質管理
  - data.quality: 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）

その他ユーティリティ:
- settings（kabusys.config.Settings）による環境変数中心の設定管理（.env 自動読み込み機能あり）
- OpenAI（gpt-4o-mini）に対する JSON Mode 呼び出し、リトライ・バックオフ制御

---

## セットアップ手順

前提:
- Python 3.10+ を想定（src レイアウトを使用）
- ネットワークアクセスが必要（J-Quants / OpenAI / ニュース RSS）
- DuckDB を利用します（pip パッケージ）

推奨手順（ローカル開発）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用に）pip install -e . が使えるパッケージ構成であれば pip install -e . を推奨

   依存例（requirements.txt がない場合の最小候補）:
   - duckdb
   - openai
   - defusedxml

3. 環境変数の準備
   ルート（プロジェクトルート）の `.env` または `.env.local` に設定を追加してください。kabusys.config は自動でプロジェクトルートの `.env` を読み込みます（CWD に依存しません）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須（最低限）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key

   ETL / 実行に使う他の例:
   - KABU_API_PASSWORD=your_kabu_station_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KILL_FLAG_CLEAR_ON_START=0
   - CPU_THRESHOLD_PCT=90.0
   - MEMORY_THRESHOLD_PCT=85.0
   - DISK_THRESHOLD_PCT=90.0
   - KABUSYS_ENV=development  # 有効値: development / paper_trading / live
   - LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR/CRITICAL

   参考: config._require が必須としているキーが未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN が未設定だと get_id_token 呼び出しでエラー）。

4. データディレクトリ作成
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）や監査 DB の格納先ディレクトリが存在することを確認してください。init_audit_db は親ディレクトリを自動作成しますが、他処理もファイル作成権限が必要です。

---

## 使い方（代表的なサンプル）

以下は Python スクリプトや REPL から呼び出すサンプルです。

- DuckDB 接続準備（例）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントを生成（LLM 使用）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("書き込んだ銘柄数:", n_written)

- 市場レジームをスコア（ETF 1321 の MA200 とマクロニュース）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB を初期化（独立 DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  # 既存接続へスキーマだけ追加する場合:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=False)

- J-Quants API を直接呼ぶ
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,31))

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- OpenAI / J-Quants の API 呼び出しはネットワークエラーやレート制限により失敗する可能性があります。モジュール内でリトライやフォールバックは行われていますが、ログや返却値を確認してください。
- LLM 呼び出しにはコストが発生します。テスト時はモックまたは少量のサンプルで検証してください。

---

## 環境変数（主な項目）

kabusys.config.Settings が参照する主な環境変数（デフォルトや必須情報含む）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（get_id_token のため）
- KABU_API_PASSWORD (必須 for kabu API): kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY (必須 for NLP/Regime unless api_key passed)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意): LINE 通知用
- DUCKDB_PATH (任意): デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意): 監視用 sqlite パス（デフォルト "data/monitoring.db"）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視関連）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視関連）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env 読込:
- プロジェクトルート（__file__ の親階層から .git または pyproject.toml を探索）で `.env` / `.env.local` を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - JQUANTS_REFRESH_TOKEN や OPENAI_API_KEY がないと該当機能はエラーになります。`.env.example` を参考に .env を作成してください。

- DuckDB ファイルの作成権限エラー
  - DUCKDB_PATH の親ディレクトリに書き込み権限があるか確認してください。init_audit_db は親ディレクトリを自動作成しますが、その他のコードは事前にディレクトリが必要な場合があります。

- J-Quants のレート制限 / HTTP エラー
  - jquants_client にリトライ / レート制御があるものの、継続的な 401（認証）や 5xx エラーは対処が必要です。get_id_token の実行やトークンの期限を確認してください。

- OpenAI レスポンスパースエラー
  - news_nlp および regime_detector はレスポンスの JSON パースに失敗した場合に警告ログを残し、安全側のスコア（0.0 等）で継続します。テスト時は _call_openai_api をモックできます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等、ETLResult）
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — JPX カレンダー管理・営業日ユーティリティ
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブルの DDL / 初期化ユーティリティ
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

各モジュールは README 内で触れた API を提供しており、テスト時や本番時の振る舞い（例: LLM 呼び出しのモック、.env 自動読込の無効化）を想定した設計がなされています。

---

## ライセンス / コントリビューション

（本リポジトリのライセンス表記やコントリビューションの手順が別にあればここに追記してください）

---

以上がプロジェクトの概要・セットアップ・利用方法のまとめです。必要であれば README に含めるサンプルスクリプトや .env.example の具体例、CI / デプロイ手順、より詳細な API リファレンスを追加できます。どの情報がさらに欲しいか教えてください。