# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → 特徴量計算（リサーチ） → AI ニュースセンチメント → 市場レジーム判定 → 監査ログ、などの機能を提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に格納する ETL パイプライン
- ニュースを収集して OpenAI を用いた銘柄別センチメントスコアを生成する AI モジュール
- ETF ベースの長期移動平均とマクロニュースを組み合わせた市場レジーム判定
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）・特徴量探索ツール
- データ品質チェック（欠損・重複・スパイク・日付整合性）モジュール
- 発注・約定の監査ログ用スキーマ初期化ユーティリティ

設計上の注力点：
- ルックアヘッドバイアスを防ぐ日付扱い
- DuckDB を用いた高速なローカル処理
- OpenAI（gpt-4o-mini）の JSON Mode を利用した堅牢な API 呼び出し
- ETL の冪等性（ON CONFLICT 等）と堅牢なリトライ・レート制御

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得 / DuckDB への保存（株価/財務/カレンダー）
  - pipeline: 日次 ETL のエントリ（run_daily_etl 等）
  - quality: データ品質チェック（missing/duplicates/spike/date_consistency）
  - news_collector: RSS からニュースを取得・前処理するユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）テーブルの初期化
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: 汎用統計（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime を算出
- research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定系
  - config.settings: .env / .env.local / 環境変数から設定を読み込み（自動ロード可/無効化可）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 記法を使用）
- Git が利用可能な環境（プロジェクトルート自動検出に利用）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - bash 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install -e . 
   - 必要な主要依存（抜粋）:
     - duckdb
     - openai
     - defusedxml
   - （pyproject.toml / requirements.txt がある前提でそちらからインストールしてください）

3. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を配置して設定を読み込めます。
   - 自動読み込みはデフォルトで有効です（config モジュールがプロジェクトルートを .git / pyproject.toml から探索します）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETLで必要）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系で使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（オプションだが多くの運用で必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
   - その他（任意/デフォルトあり）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - 注意: config.Settings は必須変数未設定時に ValueError を投げます。

5. ディレクトリと DB 用ディレクトリ作成
   - デフォルトで使用する path（data/ 等）を作成してください。
     - mkdir -p data

---

## 使い方（主なユースケース）

以下は Python REPL やバッチスクリプトから呼び出す際の例です。

- 設定読み込み
  - from kabusys.config import settings
  - settings.duckdb_path などでパスを取得できます。

- DuckDB 接続を開く
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 銘柄ニュースの AI スコアリング（ai_scores へ書込）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")  # api_key 省略時は env を参照

- 市場レジーム判定（market_regime へ書込）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- 監査ログ DB を初期化する
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能

- ファクター計算（研究用途）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=date(2026,3,20))
  - vol = calc_volatility(conn, target_date=date(2026,3,20))
  - val = calc_value(conn, target_date=date(2026,3,20))

- 将来リターン・IC 等の計算
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  - fwd = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
  - ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  - summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

- RSS を取得する（ニュース収集の一部）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - 取得した Article は raw_news に格納するために前処理して DB に挿入する実装を呼び出してください（プロジェクトの ETL 部分と組み合わせて利用）。

注意点：
- AI モジュールは OpenAI の JSON Mode を利用するため、API キーが必須です。API 呼び出しは失敗時にフェイルセーフとしてスコア 0 等にフォールバックする設計が多くありますが、キー未設定では ValueError が発生します。
- ETL / API 呼び出しはレート制御・リトライが組み込まれていますが、運用時は J-Quants / OpenAI の利用ポリシーを順守してください。

---

## 重要な環境変数（まとめ）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
  - KABU_API_PASSWORD — kabu API パスワード（実運用時）
- 任意 / デフォルトあり
  - KABUSYS_ENV — development / paper_trading / live（default: development）
  - LOG_LEVEL — ログレベル（default: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db

.env.example をプロジェクトルートに置いて設定値を作成してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージの src/kabusys 配下を抜粋）

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: pipeline の ETLResult 再エクスポート等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（zscore_normalize は data.stats から利用）
  - ai, data, research 各モジュールにさらに細分化された関数群が存在

上記以外にも execution / monitoring / strategy 等の名前空間が __init__ で想定されています（現在のコードベースで実装済みのモジュールを確認してください）。

---

## 運用上の注意点

- ルックアヘッドバイアス対策: 多くのモジュールは date 引数を必須にし、date.today() を内部で直接参照しない設計です。バッチ実行時は対象日を明示してください。
- DuckDB executemany の挙動: 一部の関数は DuckDB のバージョン依存の制約（empty params を executemany へ渡せない）を考慮しています。空リストを渡さないガードが組まれていますが、DuckDB のバージョンに注意してください。
- OpenAI / J-Quants のエラーハンドリング: 5xx や 429 等はリトライしますが、API レートや課金に注意してください。
- RSS の SSRF 対策: news_collector はリダイレクト検査・プライベートIP拒否・受信サイズ制限等を組み込んでいます。外部フィードを追加する際も信頼できるソースを使用してください。

---

## 開発 / テスト

- 自動環境変数読み込みを無効化して単体テストを実行する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出しはモック化してユニットテストを記述してください（コード中で _call_openai_api や _urlopen 等を差し替え可能）。

---

以上が KabuSys の概要・セットアップ・主要な使い方です。  
追加で README に載せたいサンプルスクリプトや運用ガイド（CI / デプロイ手順・Slack 通知設定例・kabu ステーション連携方法など）があれば、その内容に合わせて追記します。