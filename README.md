# KabuSys

日本株向けの自動売買 / データプラットフォーム共通ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（発注/約定トレース）、カレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を備えた内部ライブラリ/システム基盤です。

- J-Quants API を用いた株価・財務・カレンダーの差分ETL（rate limit / retry 対応、冪等保存）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）および市場レジーム判定
- DuckDB を利用したデータ保存・集計
- データ品質チェック（欠損・スパイク・重複・日付整合性検査）
- リサーチ用ファクター計算・特徴量解析ユーティリティ（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマ初期化・ユーティリティ

設計の共通方針として「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ（API障害時の継続）」「外部副作用の分離（研究コードが発注を行わない）」を重視しています。

---

## 機能一覧（主要）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、重要環境変数取得ラッパー（kabusys.config.settings）
  - 自動読み込み無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ ETL（kabusys.data.pipeline / etl）
  - run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl
  - ETL 結果を ETLResult で返却・ログ化

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save の一体型（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - save_daily_quotes / save_financial_statements / save_market_calendar 等

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキング除去、ID 生成、SSRF 対策、raw_news への保存向けユーティリティ

- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄単位のニュース統合→OpenAI でスコア化→ai_scores に書き込み（バッチ・バリデーション・リトライ制御）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離 + マクロニュース LLM センチメントの合成で日次レジーム判定（bull/neutral/bear）を market_regime に保存

- 研究（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）との連携

- データ品質（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル DDL、インデックス、init 関数（冪等）

---

## 必要環境・依存

- Python 3.10 以上（型注釈に `X | None` などを利用）
- 主な依存パッケージ（インストールが必要）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: urllib, json, logging, datetime 等）

※ 実行環境によっては追加で HTTP/SSL 関連パッケージが必要になることがあります。requirements.txt を用意している場合はそちらを利用してください。

---

## 環境変数（主な必須項目）

プロジェクトは .env / .env.local による設定を想定します。自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。

主に必要となる環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）

.env.example をプロジェクトに置いて参考にしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （もし setup.py / pyproject.toml があれば）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて .env.local）を作成し、上記必須変数を設定
   - 自動ロードを阻止したいテスト時等は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. ディレクトリ・DB の準備
   - デフォルトは data/ 以下に DuckDB ファイルや PID ファイルを置きます。必要に応じて作成:
     - mkdir -p data

---

## 使い方（簡単な例）

以下は Python から直接呼び出す例です（スクリプト化して cron / Airflow 等から実行する想定）。

- DuckDB 接続を作成して日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアを生成する（OpenAI APIキーが環境変数 OPENAI_API_KEY にある場合）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定を実行する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB を初期化する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます

注意:
- ai モジュールは OpenAI API を直接呼び出します。テスト時は内部の _call_openai_api をモックする設計になっています。
- run_daily_etl 等は内部で ETL の各ステップを個別にハンドルし、失敗しても他のステップは継続するため、戻り値（ETLResult）を確認して運用の判断を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要なディレクトリ・ファイル一覧（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — 銘柄ごとのニュースセンチメント解析
    - regime_detector.py              — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save）
    - pipeline.py                     — ETL パイプライン / run_daily_etl 等
    - etl.py                          — ETL の公開インターフェース（ETLResult 等）
    - stats.py                        — z-score 正規化など統計ユーティリティ
    - quality.py                      — データ品質チェック
    - calendar_management.py          — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py               — RSS 取得 / 前処理
    - audit.py                        — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラ/バリュー計算
    - feature_exploration.py          — 将来リターン / IC / summary
  - monitoring/ (存在が README の対象外の可能性あり)
  - strategy/ execution/ (コードベースに置かれている場合に各種戦略・発注ロジックを想定)

（実際のリポジトリではさらに細かなファイル・ユーティリティやテストが配置されている可能性があります。）

---

## 運用上の注意点

- ルックアヘッドバイアス防止: 多くの関数は内部で date.today() を直接参照せず、明示的な target_date を受け取る設計です。バックテストや再現性のために target_date を明示してください。
- 環境変数の管理: .env/.env.local に機密情報（APIキー等）を格納する場合はアクセス権やリポジトリ管理に注意してください。
- OpenAI 呼び出し: API 料金やレート制限に注意し、ローカルでの大量呼び出しは避けてください。テストはモックで代替できます。
- DuckDB バージョンや SQL 機能差異に依存している箇所があります。運用環境でテーブル作成・executemany の振る舞いを事前に確認してください。

---

## テスト / 開発者向けヒント

- ai モジュールの外部 API 呼び出しは各モジュール内の _call_openai_api を patch/mocking することで簡単に差し替え可能です（ユニットテスト向け）。
- J-Quants クライアントは _request の挙動をモックするとページネーションやリトライロジックのテストが容易です。
- 環境変数の自動ロードはテスト時に邪魔になる場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。

---

必要であれば README にサンプル .env.example、requirements.txt、簡易の CLI 実行スクリプト例（run_etl.py など）を追加できます。追加希望があれば教えてください。