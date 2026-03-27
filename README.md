# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）によるデータ取得、ニュースのNLP分析（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）等を含むモジュール群を提供します。

主な目的
- J-Quants API からの差分ETL（株価/財務/カレンダー）
- RSS ニュース収集とOpenAIによる銘柄センチメント付与
- 市場レジーム判定（MA200 と マクロニュースの合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧

- kabusys.config
  - 環境変数読み込み（.env / .env.local の自動ロード）と設定アクセス（settings）
- kabusys.data
  - ETL（pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（jquants_client）: 認証・ページネーション・保存（DuckDB への冪等保存）
  - カレンダー管理（calendar_management）：営業日判定 / next/prev / calendar_update_job
  - ニュース収集（news_collector）：RSS 取得・前処理・raw_news への保存
  - データ品質チェック（quality）：欠損/重複/スパイク/日付不整合
  - 監査ログ初期化（audit.init_audit_db / init_audit_schema）
  - 統計ユーティリティ（stats.zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースをまとめてOpenAIに投げ、銘柄ごとの ai_scores を作成
  - regime_detector.score_regime: ETF1321のMA200乖離とマクロニュースのLLMセンチメントを合成して market_regime に書き込み
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

設計上の注意点（主な方針）
- ルックアヘッドバイアスを避けるため datetime.today() 等を直接ループ内で参照しない設計
- DuckDB を用いた SQL + Python のハイブリッド実装
- 外部 API 呼び出しにはリトライ・バックオフ・フェイルセーフを実装
- DB 書き込みは基本的に冪等化（ON CONFLICT DO UPDATE 等）を実施

---

## 必要環境 / 依存

- Python 3.10+
  - (PEP 604 の | 型ヒント等を利用しているため最低 3.10 が必要)
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

推奨のインストール手順（例）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（任意で requirements.txt を作成して管理）
  - pip install duckdb openai defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境作成と依存インストール（上記参照）
3. 環境変数を設定
   - 推奨: プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 必須（アプリ側で参照される主要な環境変数）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot Token
     - SLACK_CHANNEL_ID: Slack のチャンネル ID
     - OPENAI_API_KEY: OpenAI を利用する場合（news_nlp / regime_detector）
   - 任意
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
4. DuckDB 初期スキーマ / 監査DB 初期化（必要に応じて）
   - 監査テーブル初期化例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - ETL 等で使用する DB は settings.duckdb_path を利用してください。

サンプル .env（.env.example）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（抜粋・例）

以下は主要機能をプログラム的に利用する例（簡易版）です。詳細は各モジュールの docstring を参照してください。

基本準備
- 設定と DB 接続
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次）
- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
  print(result.to_dict())

ニューススコアリング（OpenAI required）
- ニュースセンチメントを算出して ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を使用
  print(f"書き込み件数: {written}")

市場レジーム判定（OpenAI required）
- ETF 1321 の MA200 とマクロニュースを合成して market_regime に書き込む
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

研究系ユーティリティ（ローカル分析）
- モメンタム / ボラティリティ / バリュー等の計算
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs))

RSS ニュース取得（単体）
- RSS フィードを取得してローカルで加工確認
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])

監査DB 初期化（発注/約定トレース用）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可能

設定オブジェクトの参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)

ログレベルや実行環境は settings.env / settings.log_level で制御できます。

---

## ディレクトリ構成

リポジトリ（ソース）の概略（主要ファイル・フォルダ）

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py                    # ニュース NLP（OpenAI） -> ai_scores
      - regime_detector.py             # 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py              # J-Quants API クライアント + 保存関数
      - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      - etl.py                         # ETL インターフェース（ETLResult 再エクスポート）
      - news_collector.py              # RSS 収集＆前処理
      - calendar_management.py         # 市場カレンダー管理
      - quality.py                     # データ品質チェック
      - stats.py                       # 共通統計ユーティリティ
      - audit.py                       # 監査ログ（DDL / 初期化）
    - research/
      - __init__.py
      - factor_research.py             # モメンタム/ボラティリティ/バリュー等
      - feature_exploration.py         # 将来リターン / IC / 統計サマリー
    - monitoring/ (発注・監視系は別モジュールに分離想定)
    - strategy/ (戦略実装は別モジュールに配置想定)
    - execution/ (注文送信・ブローカー連携)
- pyproject.toml / setup.cfg (プロジェクトルートにある想定)
- .env.example (環境変数テンプレート想定)

---

## 運用上の注意 / ベストプラクティス

- 機密情報（J-Quants トークン、OpenAI キー、Kabu API パスワード等）は Git 管理下に置かないでください。`.env.local` を CI/運用側で安全に管理することを推奨します。
- OpenAI 呼び出しはレートや費用に注意して運用してください。ローカルテスト時は API 呼び出しをモックすることを推奨します（各モジュールはテスト向けに _call_openai_api の差し替えを想定）。
- ETL は差分更新＋バックフィルを行います。初回ロード時はデータ量に注意し、J-Quants API のレート制限に従ってください。
- DuckDB はローカル環境で高速に動作しますが、複数プロセスで同時に書き込む場合は運用設計に注意してください。
- KABUSYS_ENV は development / paper_trading / live を取り、live 環境では発注等の操作に特に注意してください。

---

## 参考 / 追加情報

- 各モジュールの詳細な挙動はソース（docstring）に詳細に記載しています。特に ai/news_nlp.py と ai/regime_detector.py は OpenAI 呼び出し・リトライ・レスポンス検証を丁寧に実装していますので、実運用前に必ず挙動を確認してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に行います。テスト時に自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

何か特定の機能の使い方や README に追加してほしい節（CI 設定、実運用チェックリスト、API レート管理の詳細など）があれば教えてください。README の改善案を反映して更新します。