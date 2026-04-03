# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取り込み）、ニュースセンチメント（OpenAI）、市場レジーム判定、データ品質チェック、監査ログ（約定トレース）など、アルゴリズムトレードに必要な基盤機能を収めています。

---

## 特徴（概要）

- J-Quants API 経由で
  - 日次株価（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  をフェッチし、DuckDB に冪等保存（ON CONFLICT / DO UPDATE）。
- ニュース（RSS）収集と前処理、LLM（OpenAI）で銘柄ごとのセンチメント付与（ai_scores テーブル）。
- 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントの合成）。
- データ品質チェック（欠損、重複、スパイク、日付整合性）。
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化ユーティリティ。
- DuckDB を中心としたローカルデータプラットフォーム設計（テスト可能でバックテストに注意したルックアヘッド回避設計）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API の取得・保存（fetch_* / save_*）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ヘルパー
  - quality: データ品質チェック（欠損/重複/スパイク/日付不整合）
  - news_collector: RSS 取得・正規化・保存
  - calendar_management: 市場カレンダー判定・更新ジョブ
  - audit: 監査ログ用スキーマ初期化ユーティリティ
  - stats: 汎用統計（z-score 正規化）
- ai/
  - news_nlp: ニュースをバッチで OpenAI に投げて銘柄ごとのスコア化
  - regime_detector: ETF の MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config:
  - Settings: 環境変数からの設定読み込み（.env/.env.local の自動ロード機能あり）

---

## 動作環境 / 依存関係

- Python 3.10 以上（| 型ヒントや一部の構文のため）
- 主なライブラリ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, json 等

必要なパッケージはプロジェクト配布に合わせて `pyproject.toml` / `requirements.txt` を用意してください。例（最低限）:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の主要ライブラリをインストール）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと、自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=＜J-Quants のリフレッシュトークン＞
     - OPENAI_API_KEY=＜OpenAI の API キー＞
     - KABU_API_PASSWORD=＜kabu API のパスワード（発注系を使う場合）＞
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development | paper_trading | live

   Settings クラス経由で各種設定にアクセスできます（kabusys.config.settings）。

5. 初期 DB スキーマ（監査ログなど）を用意する場合は、DuckDB に接続して初期化してください（例は下記）。

---

## 使い方（主なユースケースと例）

以下はライブラリを直接インポートして利用する例です。適宜 logging を設定して実行してください。

- 共通: 設定と DuckDB 接続

  from kabusys.config import settings
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行（株価 / 財務 / カレンダーの差分取得と品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

  注意:
  - J-Quants の認証は settings.jquants_refresh_token を用いて自動的に ID トークンを取得します。
  - run_daily_etl は各ステップで個別に例外を扱い、ETLResult を返します。

- ニュースセンチメント（当日のニュースウィンドウをスコアリング）

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境に設定しておく
  print(f"書き込んだ銘柄数: {n}")

  注意:
  - API キーは第3引数 api_key に渡すか環境変数 OPENAI_API_KEY を設定します。
  - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）で計算されます。

- 市場レジーム判定

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キー必要

  - 1321（ニッケイ ETF）の 200 日 MA 乖離とマクロニュースセンチメントを合成し market_regime テーブルへ保存します。

- 監査ログ（スキーマ）初期化

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  # これで signal_events / order_requests / executions テーブルとインデックスが作成されます

- J-Quants の個別フェッチ（ライブラリ経由）

  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  # 保存は save_daily_quotes(conn, records) を使います（ETL 内で既に呼ばれます）

---

## 環境変数と設定（settings）

kabusys.config.Settings はアプリケーションの設定を提供します（プロパティとしてアクセス）。

主なキー:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須発注利用時)
- KABU_API_BASE_URL (省略時 http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM 呼び出しに必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知に使用可能)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB path)
- PID_FILE_PATH / KILL_FLAG_PATH（監視用）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込みは OS 環境変数を保護し、.env.local は .env を上書きします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
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
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*.py (ファクター / 統計ユーティリティ)

（上記は要点抜粋です。詳細は各モジュール内の docstring を参照してください）

---

## 運用上の注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス対策:
  - モジュールは date.today() / datetime.today() を内部で参照しないように設計されています（外部から target_date を渡すことでバックテスト安全を担保）。
  - データ取得クエリは target_date 未満 / 以前 を明確に指定しており、未来データ参照を防ぎます。
- 冪等性:
  - データ保存は可能な限り ON CONFLICT DO UPDATE / INSERT … ON CONFLICT を用いて冪等に実装。
- フェイルセーフ:
  - LLM API 失敗時はスコアを中立（0.0）でフォールバックする等、外部 API の失敗が全体を停止させない設計。
- セキュリティ:
  - news_collector では SSRF 対策・XML パースに defusedxml を使用・最大受信バイト数制限などを実施。
- レート制限:
  - J-Quants クライアントは固定間隔スロットリング（デフォルト 120 req/min）を実装。

---

## 貢献 / 開発者向け

- コードの理解は各モジュールの docstring を参照してください。ユニットテストや CI 設定があれば合わせて追加してください。
- 環境変数や機密情報は `.env` に置き、 `.env.example` をリポジトリに含めることを推奨します（このリポジトリではサンプルとして README の「環境変数」セクションを参照）。

---

必要に応じて README に入れる「.env.example」や実行スクリプト、systemd / supervisor 用の起動例、監視とアラートの設定サンプルなども作成できます。追加したい項目があれば教えてください。