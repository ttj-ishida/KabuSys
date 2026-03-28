# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、研究用ユーティリティ、監査ログ（約定追跡）などを含むモジュール群を提供します。

- 開発バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去等）
- OpenAI を用いたニュース・マクロセンチメント評価（銘柄ごとのスコア、マーケットレジーム判定）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および研究支援ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）用スキーマ初期化ユーティリティ

設計上の特徴:

- Look-ahead bias を避ける（date を引数で与え、内部で date.today() を盲目的に参照しない実装）
- DuckDB を主なデータストアに利用（軽量で高速な分析に適する）
- 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）とリトライ・レート制御を備えた API クライアント
- セキュリティ考慮（RSS の SSRF 対策、defusedxml の使用等）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API からの取得・DuckDB 保存（株価・財務・カレンダー・上場銘柄情報）
  - pipeline: 日次 ETL の実装（run_daily_etl 等）
  - news_collector: RSS 収集、前処理、raw_news への保存ロジック
  - calendar_management: 営業日判定やカレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル定義・初期化（signal/order_request/executions）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価し ai_scores へ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime へ保存
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value 等
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー等
- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルートを .git or pyproject.toml で検出）
  - 環境変数の取得ユーティリティ（必須値は _require でチェック）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の Union 型等を使用）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（必要に応じて）
  - （ネットワーク要求を行うため標準ライブラリの urllib を使用）

※開発用の requirements.txt / pyproject.toml はプロジェクトに合わせて用意してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしプロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （開発環境では flake8 / pytest 等を追加）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成することで自動読み込みされます（.git または pyproject.toml がある親ディレクトリを探索）
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

例: .env の主要項目
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

> 備考: kabusys.config は OS 環境変数を優先し、.env.local があればそれで上書きします。

---

## 使い方（代表的な例）

以下は Python スクリプトや対話環境で使う例です。

- DuckDB 接続の準備（デフォルトのパスを使用する場合）:

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI を使って ai_scores に書き込む）:

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数

- 市場レジーム判定（MA200 とマクロセンチメントを合成）:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は OPENAI_API_KEY を参照

- 監査ログ DB の初期化（監査専用 DB を作る場合）:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査用テーブルにアクセス可能

- ファクター/研究ユーティリティの使用例:

  from kabusys.research.factor_research import calc_momentum, calc_value
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))   # list[dict]
  val = calc_value(conn, date(2026, 3, 20))

- データ品質チェック:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（ai.news_nlp / ai.regime_detector）
- SLACK_BOT_TOKEN — Slack 通知用（プロジェクトで Slack 通知を使う場合）
- SLACK_CHANNEL_ID — Slack の投稿先チャンネル ID
- KABU_API_PASSWORD — kabu（注文連携）API のパスワード

任意（デフォルト値あり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルートを .git または pyproject.toml で探索し、.env/.env.local を自動読み込みします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成です（抜粋）:

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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（プロジェクト全体のファイルやドキュメントはリポジトリを参照してください）

---

## 注意事項 / 運用上のポイント

- OpenAI / J-Quants API 呼び出しには適切な API キーを設定してください。API のレート制限や課金に注意してください。
- news_nlp と regime_detector は外部 API（OpenAI）に依存します。API 呼び出し失敗時はフェイルセーフ（スコアを 0 にフォールバック）する実装の箇所がありますが、運用設計での監視が重要です。
- DuckDB のスキーマはプロジェクトの仕様に従って事前に作成しておくか、ETL 実行時に必要なテーブル初期化処理を実装してください（audit.init_audit_db は監査テーブルの初期化ユーティリティを提供します）。
- ETL 実行・API 呼び出しは十分なログ出力を行うため、LOG_LEVEL を適切に設定して運用監視を行ってください。

---

## 貢献 / テスト

- テストフレームワーク（pytest 等）や linters を導入することを推奨します。
- 外部 API 呼び出し部はモック可能な設計になっているため、ユニットテストでの差し替えが容易です（例: ai モジュール内の _call_openai_api を patch）。

---

必要があれば、README に以下の追加を行います：
- 詳細な DB スキーマ（テーブル定義）
- サンプル .env.example の具体的な内容
- docker-compose / systemd ユニットのサンプル（運用用）
- CI / CD やデプロイ手順

どの追加を希望しますか？