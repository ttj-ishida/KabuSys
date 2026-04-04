# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、ファクター計算、監査ログ・発注履歴管理、マーケットカレンダー管理など、量的運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ ETL
  - J-Quants API から株価（日次）・財務データ・上場情報・市場カレンダーを差分取得し DuckDB に保存
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS から記事を収集し前処理して raw_news に冪等保存（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントを LLM（gpt-4o-mini）で評価して ai_scores に保存
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM の混合スコア）
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算ユーティリティ
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計要約
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 発注フローを UUID ベースで完全トレース
- マーケットカレンダー管理
  - market_calendar を用いた営業日判定／次営業日検索／カレンダー更新ジョブ
- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）と Settings API

---

## 必要条件 / 依存関係

- Python 3.10+（typing の | 演算子などを使用）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP/URL/JSON 等を使用（urllib 等）

※ requirements.txt はリポジトリに含まれていない想定のため、必要に応じて上記パッケージを pip でインストールしてください。

例:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

KabuSys は環境変数から設定を読み取ります。プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード（発注周りで使用）
- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必要に応じて)  
  OpenAI API キー（news_nlp / regime_detector などで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  通知用（LINE）トークン / ユーザ ID
- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START (任意)  
  実行プロセス監視用ファイルパス設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (任意)  
  監視しきい値（%）
- KABUSYS_ENV (optional)  
  値: development / paper_trading / live
- LOG_LEVEL (optional)  
  DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の書式は typical な KEY=VALUE をサポート。`.env.local` は .env より優先で読み込まれます。

---

## セットアップ手順（ローカル開発向け簡易ガイド）

1. Python 環境の準備
   - Python 3.10+ を用意（pyenv / venv 等を推奨）
2. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - その他、プロジェクト固有の依存があれば追加
3. プロジェクトルートに .env を作成
   - .env.example を参考に最低限 JQUANTS_REFRESH_TOKEN 等を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=./data/kabusys.duckdb
4. データディレクトリの作成（必要なら）
   - mkdir -p data
5. DuckDB 初期化（監査ログ用 DB 例）
   - Python REPL またはスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
6. ログレベル設定
   - 環境変数 LOG_LEVEL=INFO など

---

## 使い方（主要 API の例）

以下はライブラリを直接呼び出す簡単な例です。実行は適宜環境変数を設定してから行ってください。

- DuckDB 接続の作成
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを評価して ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

  ※ OPENAI_API_KEY が必要（引数 api_key を渡すことも可）

- 市場レジーム判定を実行
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算（研究用途）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))

- 監査ログテーブルの初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

注意点:
- AI（OpenAI）呼び出しは課金が発生します。API キーと利用量に注意してください。
- ETL 実行は J-Quants API の利用制限に従ってください（本ライブラリはレート制御を試みますが、API 側ルールを遵守してください）。
- モジュール設計上、バックテストや研究目的で呼ぶ場合は Look-ahead バイアスを避けるために target_date を明示することが推奨されています。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約 → OpenAI（gpt-4o-mini）で銘柄ごとスコアリング → ai_scores へ保存
    - regime_detector.py
      - ETF 1321 の 200 日 MA とマクロニュース LLM 評価を合成して market_regime を更新
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar の判定・次営業日/前営業日検索・更新ジョブ
    - pipeline.py
      - ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
    - jquants_client.py
      - J-Quants API クライアント（fetch/save/認証/レート制御/リトライ）
    - news_collector.py
      - RSS フィード収集と raw_news 保存（SSRF 対策、正規化、ID 生成）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL と初期化ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、ファクター統計、ランク関数等

（上記は主要モジュールの要約です。各モジュール内に詳細な設計方針・フェイルセーフ処理が実装されています）

---

## 実運用上の注意

- 環境（KABUSYS_ENV）が `live` の場合、発注や外部システムへの送信など取り扱いに注意してください（本コードベースは発注周りの基盤設計を含みますが、証券会社 API と接続して実運用する前に十分なレビューとテストが必要です）。
- OpenAI の呼び出しは冪等やリトライ・フォールバック設計がありますが、API 仕様変更時に挙動が変わる可能性があります。
- DuckDB のバージョン差異により executemany の挙動等があるため、運用環境での検証を推奨します。
- RSS 収集では SSRF 対策・応答サイズ上限など基本的な安全対策を実装済みですが、運用時はソース管理・スロットリングを適切に設定してください。

---

## 参考（短い FAQ）

- Q: .env の自動読み込みを無効化するには？
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: OpenAI API のキーを関数呼び出しごとに渡せますか？
  - A: はい。news_nlp.score_news や regime_detector.score_regime は api_key 引数を受け取ります。未指定の場合は環境変数 OPENAI_API_KEY を参照します。

- Q: J-Quants の認証トークンはどのように扱われますか？
  - A: refresh token（JQUANTS_REFRESH_TOKEN）を設定し、jquants_client.get_id_token が id_token を取得してページネーション間でキャッシュします。401 時に自動リフレッシュします。

---

この README はコードベースの主要部分を簡潔にまとめたものです。各モジュール内に詳細な docstring が含まれているため、実装や仕様の詳細は該当ファイルを参照してください。必要であれば、セットアップの CI / requirements.txt / サンプルスクリプト等を別途追加できます。