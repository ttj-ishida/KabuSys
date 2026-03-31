# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買用ライブラリです。J-Quants / RSS / OpenAI 等の外部データを取り込み、DuckDB 上で ETL・品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ（発注フロー追跡）を行うためのユーティリティ群を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時の継続）」です。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local からの自動読み込み（パッケージルート検出）
  - 必須設定取得とバリデーション（settings オブジェクト）

- データ ETL（J-Quants）
  - 日足（OHLCV）、財務データ、JPX市場カレンダーの差分取得・保存（ページネーション対応・レート制御・リトライ）
  - ETL の統合エントリ：run_daily_etl（品質チェック付き）

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付整合性等の検出（QualityIssue 型で集約）

- ニュース収集・前処理
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、最大サイズ制限）
  - raw_news / news_symbols への冪等保存サポート

- ニュース NLP（OpenAI / gpt-4o-mini）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む（score_news）
  - マクロニュースのセンチメントを用いた市場レジーム判定（score_regime）

- リサーチ用ユーティリティ
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査スキーマ初期化（init_audit_schema / init_audit_db）
  - 発注フローを UUID で追跡する設計

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.9+（コードは型ヒント等を使用）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している前提です。ローカルで開発する場合は pip install -e . も想定してください。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（パッケージの __file__ を基準にプロジェクトルートを探索します）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数（必須は明記）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（score_news / score_regime 等で使用）
     - KABU_API_PASSWORD (必須 if using kabu API) — kabuステーション API パスワード
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須 if Slack notifications used)
     - SLACK_CHANNEL_ID (必須 if Slack notifications used)
     - DUCKDB_PATH — デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 環境 ('development'|'paper_trading'|'live')（デフォルト: development）
     - LOG_LEVEL — ログレベル ('DEBUG','INFO',...)（デフォルト: INFO）

4. データベース初期化（監査ログ等）
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - 上記は parent ディレクトリを自動作成します。":memory:" を指定するとインメモリ DB になります。

---

## 使い方（代表的な API）

以下は主要機能の簡単な使用例です。実運用ではエラーハンドリングやログ設定を適切に行ってください。

- Settings（環境変数取得）
  - from kabusys.config import settings
  - settings.jquants_refresh_token
  - settings.env / settings.is_live など

- DuckDB 接続を作って ETL を実行
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントのスコアリング
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
  - print(f"scored {count} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査スキーマ初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
  - conn = duckdb.connect(str(settings.duckdb_path))
  - init_audit_schema(conn, transactional=True)

- J-Quants API を直接操作
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  - token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
  - recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意:
- OpenAI を利用する機能は OPENAI_API_KEY が必要です（score_news / score_regime）。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）存在を前提とします。スキーマ初期化は本リポジトリ外で行う設計を想定しています（必要に応じてスキーマ作成スクリプトを用意してください）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ基本情報（__version__）
  - config.py — 環境変数 / .env の自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄別に集約して OpenAI に送り ai_scores に書き込む
    - regime_detector.py — ETF(1321) の MA200 とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、取得＆保存ロジック
    - pipeline.py — ETL（run_daily_etl 等）と ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理＆営業日ユーティリティ
    - news_collector.py — RSS 収集・前処理・保存支援（SSRF対策など）
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付整合性）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ（signal_events, order_requests, executions）スキーマ 初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

簡易ツリー表示（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 運用上の注意点

- ルックアヘッドバイアス防止: ほとんどの処理は date 引数を外部から与え、内部で datetime.today()/date.today() を直接参照しない設計になっています。バックテスト等で正しく過去情報のみを使うため、target_date を明示してください。
- API キー管理: トークンや API キーは .env に保存して安全に管理してください。公開リポジトリにアップロードしないでください。
- 冪等性: J-Quants 保存関数や監査スキーマは基本的に冪等（ON CONFLICT）を考慮していますが、運用上のデータ整合性は監査ログやバックアップで補完してください。
- フェイルセーフ: OpenAI 等の外部 API が失敗した場合は、デフォルトやスコア 0.0 等にフォールバックして処理継続する設計になっています（ログを必ず確認してください）。

---

もし README に追加して欲しい内容（例: モジュールごとの API リファレンス、サンプル .env.example、CI / デプロイ手順など）があれば教えてください。