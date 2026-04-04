# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの市場データ取得）、データ品質チェック、ニュース収集・NLP による銘柄センチメント算出、リサーチ用ファクター計算、監査ログ（オーディット）など、バックテスト・運用で必要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作要件
- セットアップ手順
- 使い方（主要 API / 例）
- 環境変数一覧（主なもの）
- ディレクトリ構成
- 注意事項

---

プロジェクト概要
- DuckDB を内部データストアとして使用し、J-Quants API や RSS からデータを取り込み、品質チェック・加工・研究用ファクター算出、AI を用いたニュースセンチメント評価、監査ログの保持、取引実行監視のためのユーティリティを提供します。
- バックテストや運用における Look-Ahead バイアス対策や API リトライ・レート制御などの設計方針が各モジュールに反映されています。

主な機能一覧
- データ取得 / ETL
  - J-Quants から株価（daily quotes）、財務データ、上場銘柄一覧、JPX マーケットカレンダーを差分取得・保存（jquants_client, data.pipeline）
  - run_daily_etl による日次 ETL パイプライン
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合検出
- ニュース収集（data.news_collector）
  - RSS から記事を収集、前処理して raw_news に保存（SSRF 対策・トラッキング除去等の安全機構あり）
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出と ai_scores への保存
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を判定
- リサーチ（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（prices_daily, raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（data.audit）
  - シグナル → 発注 → 約定の監査テーブル作成・初期化（冪等、UTC タイムスタンプ）
- 設定管理（config）
  - .env（および .env.local）自動ロード、環境変数ラップ（settings オブジェクト）

動作要件（推奨）
- Python 3.10+
- 必須 Python ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ（urllib 等）およびプロジェクトに応じた依存が必要です。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 代表的な依存:
     - pip install duckdb openai defusedxml
   - ローカルパッケージとして editable install:
     - pip install -e .
     （プロジェクトに requirements.txt や pyproject があればそちらを利用してください）
4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き可能）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. DuckDB（監査用など）初期化例
   - Python REPL やスクリプトから:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - init_audit_db は親ディレクトリを自動作成します（":memory:" も可）。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルトは http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知関連（任意）
- DUCKDB_PATH: デフォルトデータベースパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（値をセットすると自動ロードしない）

使い方（代表的な例）

- 設定を参照する
  from kabusys.config import settings
  print(settings.duckdb_path)    # Path オブジェクト
  print(settings.jquants_refresh_token)  # 必須項目（未設定時は ValueError）

- DuckDB 接続を開く
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコアを計算・保存する
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")

  - 注意: OPENAI_API_KEY が必要（引数 api_key でも渡せます）
  - 処理は指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）に収集した記事を対象

- 市場レジームをスコアする
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数か引数で指定

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  results = calc_momentum(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（オフラインで監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数/.env 管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py             # ニュースセンチメント算出（OpenAI）
    - regime_detector.py      # 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB 保存
    - pipeline.py             # ETL パイプライン（run_daily_etl など）
    - etl.py                  # ETL インターフェース（ETLResult）
    - news_collector.py       # RSS ニュース収集（SSRF 対策等）
    - calendar_management.py  # 市場カレンダー / 営業日判定
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - audit.py                # 監査ログ DDL・初期化
  - research/
    - __init__.py
    - factor_research.py      # モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py  # 将来リターン・IC・サマリー等
  - ai, monitoring, execution, strategy  # __all__ に宣言されているサブパッケージ（存在するモジュール群に依存）

注意事項 / 設計上のポイント
- Look-Ahead バイアス対策
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は datetime.today() や date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテスト時は必ず過去の target_date を使って下さい。
- API 呼び出し
  - J-Quants クライアントはレート制御とリトライを実装していますが、API キーや利用制限に注意して運用してください。
  - OpenAI 呼び出しは gpt-4o-mini を使用する想定で JSON mode を利用しています。API 料金・レートに留意してください。
- ニュース収集の安全性
  - fetch_rss は SSRF 対策（プライベートアドレス検出、リダイレクト検査）、XML の安全パーサ（defusedxml）を採用しています。
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を起点）から .env/.env.local を自動読み込みします。テスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB バージョン互換
  - 一部コードは DuckDB の executemany の挙動（空リストの扱いなど）に合わせた実装になっています。DuckDB のバージョン互換に注意してください。

---

問い合わせ / 貢献
- コードベースの改善提案やバグ報告は Issue を立ててください。Pull Request は歓迎します。

以上。README に不足しているセットアップ細部（requirements.txt、CI、具体的な運用手順など）はリポジトリのルートに合わせて追記してください。