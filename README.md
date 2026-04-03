# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants 連携）→ データ品質チェック → ニュース収集・NLP（OpenAI）→ ファクター計算 → 監査ログ・発注追跡、を一貫して支援するモジュール群を提供します。

主な目的は、バックテスト・研究環境と実運用（kabuステーション経由の発注）を分離しつつ、安全に自動化されたデータパイプラインと意思決定（LLM を利用したニュース評価等）を実装できる基盤を提供することです。

---

## 主要機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得（ページネーション、リトライ、レート制御）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出と QualityIssue レポート
- カレンダー管理
  - 営業日判定、前後営業日取得、カレンダーの夜間更新ジョブ
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・記事の冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースからセンチメントを算出して ai_scores に書込む（score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（score_regime）
- リサーチ／ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン、IC 計算、Z-score 正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数および .env(.env.local) 自動読み込み、保護された OS 環境変数の扱い

---

## 必要な環境・依存パッケージ（例）

本リポジトリのコードは以下のようなパッケージを想定しています（バージョンは適宜固定してください）。

- Python 3.10+
- duckdb
- openai
- defusedxml

（pip 用の requirements.txt がある場合はそちらを使ってください。なければ次の例を参照してインストールしてください。）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt が無ければ:
     pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（モジュール起動時に探索）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数（利用する機能に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須で ETL を動かす場合）
   - OPENAI_API_KEY        : OpenAI の API キー（news NLP / regime 判定で必須）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注を行う場合）
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : 動作環境 ("development" | "paper_trading" | "live")
   - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)

   サンプル（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

4. データベースファイル用ディレクトリの作成
   - デフォルトだと data/ 以下を使用します。必要なら作成してください。
   - mkdir -p data

---

## 使い方（主要 API と実行例）

以下はいくつかの代表的な実行例です。実行には duckdb と必要な環境変数が設定されていることを前提とします。

- DuckDB 接続を作る（ファイル or :memory:）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュース NLP（銘柄別スコア算出）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を明示するか、OPENAI_API_KEY を環境変数で設定
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {count} codes")

- 市場レジーム判定（ETF 1321 の MA200 シグナル + マクロニュース）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存の conn に対してスキーマ適用:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- ファクター計算・リサーチユーティリティ
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- OpenAI 呼び出しは失敗時にフェイルセーフで 0.0 やスキップを返す設計ですが、API キーが未設定の場合は ValueError を送出します。
- run_daily_etl 等は内部で例外を逐次キャッチし、ETLResult にエラー内容を蓄積します。戻り値を確認してください。

---

## .env の自動読み込み

- プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定します（CWD に依存しません）。
- 自動読み込みは順序: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを無効にするには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の行パーサはシェル風の export プレフィックス、クォート、コメント処理に対応しています。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（score_news）
    - regime_detector.py     # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存関数
    - pipeline.py            # ETL パイプライン（run_daily_etl 他）
    - etl.py                 # ETL 結果型の再エクスポート
    - news_collector.py      # RSS ニュース収集
    - calendar_management.py # 市場カレンダー管理
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログスキーマ初期化
    - stats.py               # 汎用統計関数（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # forward returns / IC / summary / rank

各モジュールは DuckDB 接続オブジェクトを引数にとる関数群が多く、テスト／再利用しやすい設計になっています。

---

## 実運用上の注意

- 発注や実運用を行う際は KABU API 周りの認証情報・接続先設定およびリスク管理を十分に確認してください。デフォルトでは発注系は無効化して運用してください。
- KABUSYS_ENV を "live" に設定すると実運用用のフラグが反映される箇所があります。環境は明示的に設定してください（development / paper_trading / live）。
- LLM（OpenAI）を使う処理は API コストとレイテンシの考慮が必要です。バッチサイズやリトライ設定は各モジュールの定数で調整可能です。
- DuckDB の executemany に関する注意点（空リスト渡し不可など）に対応した実装がなされていますが、DuckDB のバージョン差異による挙動に注意してください。

---

## 開発・テスト

- モジュール内部には外部 API 呼び出しを容易にモックできる設計（関数切替／patch）があります。ユニットテスト実行時は環境変数の自動ロードを無効にすることを推奨します。
  - 例: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な設計方針やパラメータは各モジュールの docstring を参照してください（src/kabusys/** に豊富なコメントが含まれています）。必要であればサンプル .env.example、requirements.txt、起動用スクリプト等のテンプレートを追加で作成できます。