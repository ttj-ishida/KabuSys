# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
DuckDBを中心としたデータETL、ニュースのNLP解析（OpenAI利用）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

## 主な特徴
- データETL
  - J-Quants API から株価（日足）・財務情報・JPXカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション・冪等保存（ON CONFLICT）対応
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出などのチェック機能
- ニュース収集 / NLP
  - RSS 取得・正規化・保存（raw_news）
  - OpenAI（gpt-4o-mini）を用いた記事/銘柄ごとのセンチメントスコアリング（ai_scores）
- 市場レジーム判定
  - ETF(1321)の200日移動平均乖離とマクロニュース（LLM評価）を合成して日次レジーム判定
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン、IC、統計サマリ、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal / order_request / executions の監査テーブルを提供し、UUIDでフローを完全追跡
- セキュリティ対策
  - RSS収集のSSRF対策、受信サイズ制限、XML安全パーサ、APIリトライ/レート制御等を実装

---

## 必要条件
- Python 3.9+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は setup 時にインストールしてください）

※ 実行する機能により外部サービス（J-Quants, OpenAI）へのAPIキーが必要です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone …（省略）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -U pip
   - pip install -r requirements.txt
     - もし requirements.txt が無ければ、最低限以下を入れてください:
       - pip install duckdb openai defusedxml

   - 開発インストール（パッケージとして使う場合）:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（アプリケーション実行で必要になる可能性が高い）
- JQUANTS_REFRESH_TOKEN  (必須: J-Quants 用リフレッシュトークン)
- KABU_API_PASSWORD      (必須: kabu ステーション API パスワード)

任意 / 機能に応じて
- OPENAI_API_KEY         (OpenAI 呼び出しに使用; score_news / score_regime 等)
- KABU_API_BASE_URL      (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH            (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH            (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE        (paper_trading 用: instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定
- KABUSYS_ENV            (development | paper_trading | live)
- LOG_LEVEL              (DEBUG|INFO|WARNING|ERROR|CRITICAL)

---

## 使い方（簡単な例）

以下は主要な操作のサンプルコード例です。実行前に環境変数（APIキー等）を設定してください。

- DuckDB 接続例
  - Python:
    - import duckdb
    - from kabusys.config import settings
    - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（データ取得・保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- ニューススコアリング（ai_scores への書き込み）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # 対象日を指定
  - print(f"scored {n} codes")

- 市場レジーム判定（market_regime テーブルへ書き込み）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化（独立した監査DBを作る場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- AI 関連関数（score_news / score_regime）は OpenAI API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError を送出します。
- 各関数は「ルックアヘッドバイアス」を避ける設計になっており、内部で datetime.today() を参照しない場合があります。必ず target_date を明示することで過去データのみを使った再現可能な処理になります。

---

## ディレクトリ構成（主要ファイルと説明）
（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス。自動 .env ロード（.env, .env.local）を備える。
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI でスコアリングして ai_scores に保存する。
    - regime_detector.py
      - ETF1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新する。
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理、営業日判定、next/prev_trading_day 等。
    - etl.py
      - ETLResult の公開
    - pipeline.py
      - 日次ETLの主要処理（市場カレンダー、株価、財務、品質チェック）
    - stats.py
      - zscore_normalize 等の汎用統計ユーティリティ
    - quality.py
      - データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal / order_request / executions）テーブル定義・初期化
    - jquants_client.py
      - J-Quants API クライアント（認証, レート制御, 取得/保存関数）
    - news_collector.py
      - RSS 取得、正規化、SSRF 対策、raw_news への保存ロジック
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ等

---

## 実運用上の注意
- API レート制御・リトライ・フェイルセーフを多くの箇所で実装していますが、実際の稼働前にテスト環境で十分に検証してください。
- OpenAI や J-Quants など外部API利用時の料金やレートリミットに注意してください。
- DuckDB ファイルや SQLite などの永続化先のバックアップ／権限管理を行ってください。
- ETL と AI スコアリング等は時間のかかる処理となるため、適切なジョブスケジューラ/監視を使用してください。
- .env に秘密情報を格納する場合はファイルのアクセス権限に注意してください。

---

もし README に追加したい利用例、CI/CD の設定、詳細なテーブルスキーマ（DDL）、または .env.example のテンプレートが必要であれば教えてください。README をその内容に合わせて拡張します。