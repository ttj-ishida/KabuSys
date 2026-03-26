# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・AI を組み合わせた自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、レジーム判定、ファクター計算、データ品質チェック、監査ログなど、量的運用で必要となる主要コンポーネントを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() や現在時刻を不用意に参照しない）
- DuckDB を中心としたローカルデータベース設計（冪等保存を重視）
- 外部 API 呼び出しはリトライ・レート制御・フォールバック処理を備える
- テスト容易性を考慮（APIキー注入や内部関数の差し替えが可能）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API/コマンド例）
- ディレクトリ構成
- 環境変数一覧 / .env 例
- トラブルシューティング

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株の自動売買 / 研究プラットフォームを構築するためのライブラリ群
- コア技術: Python + DuckDB、J-Quants API、OpenAI（LLM）、RSS 収集

---

機能一覧
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー
  - ページネーション・トークン管理・レート制御・リトライ
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合実行 (run_daily_etl)
- ニュース関連
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - LLM を使ったニュースセンチメント / 銘柄別 ai_score の計算（news_nlp.score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジームを判定（regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research モジュール）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- データ品質チェック（quality モジュール）
- 監査ログ（audit）
  - signal → order_request → executions までのトレーサビリティ用スキーマ生成 & DB 初期化
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検出）、環境変数からの Settings 提供

---

セットアップ手順（開発・ローカル実行向け）

前提
- Python 3.10+ を推奨
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （requests などは実装に応じて追加）

例: 仮想環境とインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

2. パッケージインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb openai defusedxml

3. リポジトリのインストール（編集しながら使う場合は editable install）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 自動読み込みはデフォルトで有効。.env を読み込みたくないテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成
   - デフォルトは data/kabusys.duckdb 等なので必要に応じてディレクトリを作成してください（init 関数は親ディレクトリを自動作成する箇所もありますが念のため）。

---

使い方（主要 API / 例）

基本: settings の取得
- from kabusys.config import settings
- settings は JQUANTS_REFRESH_TOKEN 等必須値を環境変数から取得します。

DuckDB 接続
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=some_date)
- result は ETLResult（取得・保存件数や品質問題のリスト含む）

2) ニュースセンチメント（銘柄別 ai_scores）を得て DB に保存
- from kabusys.ai.news_nlp import score_news
- cnt = score_news(conn, target_date=some_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を利用します。
  - 戻り値は書き込んだ銘柄数

3) 市場レジームの判定（market_regime テーブルへ書き込み）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date, api_key=None)

4) 研究系 API（ファクター算出等）
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- fm = calc_momentum(conn, target_date)
- fv = calc_value(conn, target_date)

5) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # parent ディレクトリは自動作成

6) RSS 取得（ニュース収集）
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
- fetch_rss は NewsArticle 型のリストを返します（DB 挿入は別関数で行う想定）

注意点
- OpenAI 呼び出しはコストが発生します。API キーおよび使用料を管理してください。
- API 呼び出しや DB 書き込みは例外を投げることがあります。運用ではログ・リトライ・モニタリングを整備してください。

---

環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)  : J-Quants リフレッシュトークン（config.Settings.jquants_refresh_token）
- KABU_API_PASSWORD (必須)      : kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意)      : kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)       : Slack チャネル ID
- OPENAI_API_KEY (必須 for AI funcs) : OpenAI API キー（news_nlp / regime_detector のデフォルト参照先）
- DUCKDB_PATH (任意)            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意)            : SQLite path（モニタリング用）
- KABUSYS_ENV (任意)            : 実行環境 ("development" | "paper_trading" | "live")（デフォルト "development"）
- LOG_LEVEL (任意)              : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

.env の例（プロジェクトルートに配置）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

自動ロード
- kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）を検出して .env / .env.local を自動で読み込みます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP スコアリング（ai_scores へ書込）
    - regime_detector.py           -- 市場レジーム判定（market_regime へ書込）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch/save 関数）
    - pipeline.py                  -- ETL パイプライン / run_daily_etl
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS 収集器
    - calendar_management.py       -- 市場カレンダー & 営業日判定
    - stats.py                     -- zscore_normalize 等
    - quality.py                   -- データ品質チェック
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- momentum/value/volatility 等
    - feature_exploration.py       -- forward returns / IC / summary
  - ai, research, data 配下に各種ユーティリティ・ロジック（SQL / DuckDB 利用）

---

トラブルシューティング（よくある問題）
- ValueError: 環境変数 'XXX' が設定されていません。
  - 必須の環境変数が未設定です。README の .env 例を参考に設定してください。
- OpenAI / J-Quants API エラー・タイムアウト
  - ネットワークや API キーを確認。ライブラリはリトライを行いますが回復できない場合はログを参照。
- DuckDB ファイルが作成されない / パスが見つからない
  - DUCKDB_PATH の親ディレクトリが存在するか確認（init_audit_db は親ディレクトリを自動作成しますが、他箇所は期待挙動が異なる場合があります）
- .env 自動読み込みを無効化したい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

開発貢献 / 拡張案
- 追加のニュースソースや言語処理パイプラインの強化
- 発注実行モジュール（kabu ステーション / 証券会社 API 統合）
- 監視・アラート（Slack 連携の自動化）
- バックテスト用の時系列データ提供ラッパー

---

最後に
この README はソースコードの注釈に基づく概要です。各モジュールには詳細な docstring が含まれているため、実装の詳細や各関数の引数/戻り値は該当ファイルを参照してください。質問や追加のドキュメントが必要であればお知らせください。