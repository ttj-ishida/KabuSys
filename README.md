# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算、監査ログ管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部ユーティリティ群をまとめたパッケージです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価
- ファクター計算（モメンタム／ボラティリティ／バリュー 等）と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数管理・設定読み込み（.env 自動読み込み機能あり）

設計上の特徴として、バックテストや本番運用でのルックアヘッドバイアスに配慮した実装、ETL/DB 操作の冪等性、API 呼び出しのリトライ／レート制御、セキュリティ対策（SSRF 防止、XML の安全パース等）があります。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レート制御）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news、トラッキング除去、SSRF 対策）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 小規模統計ユーティリティ（zscore 正規化等）
- ai
  - ニュース NLP（銘柄ごとの ai_score を ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
  - OpenAI 呼び出しは JSON mode を利用しレスポンスを厳密に検証
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー等
- config
  - .env/.env.local と環境変数を自動読み込み（プロジェクトルート検出）
  - settings オブジェクトで設定値へアクセス

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... (プロジェクトルートに .git / pyproject.toml があると自動的に .env を探します)

2. Python 仮想環境を作成（推奨）
   - Python 3.10 以上を推奨（型アノテーションや union 型を利用しているため）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要最低限の依存例:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外を使う箇所があるためプロジェクトの requirements.txt があればそれを使用してください）
   例:
   - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主要な環境変数（最低限必要／推奨）
     - JQUANTS_REFRESH_TOKEN  ← J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD      ← kabuステーション API パスワード（必須）
     - OPENAI_API_KEY         ← OpenAI 呼び出しに必要（ai モジュールを使う場合）
     - KABU_API_BASE_URL      ← kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            ← DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            ← 監視用 SQLite（デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID ← LINE 通知を使う場合
   - settings オブジェクト経由で他の設定（ログレベル、閾値等）も参照できます。

5. データディレクトリ作成
   - settings.duckdb_path / settings.sqlite_path の親ディレクトリを作成しておいてください（多くの初期化関数は自動作成することもありますが事前に作成しておくと安心です）。

---

## 使い方（簡単な例）

以下は Python から直接呼び出す例です。DuckDB 接続は直接渡します。

- 共通: settings の利用例
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- ETL（日次パイプライン実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（ai.news_nlp）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリは自動作成
  ```

- J-Quants ID トークンを明示取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意:
- AI 関連関数は OpenAI API キー（OPENAI_API_KEY）の設定が必要です。キーがない場合は ValueError を送出します。
- run_daily_etl は内部で calendar_etl → prices_etl → financials_etl → 品質チェックの順で実行します。エラーは個別に記録され、ETLResult に集約されます。

---

## 環境変数 / 設定項目のまとめ

主に使用するキーの一覧（settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)  
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (ai を使う場合に必要)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — invalid な値はエラー
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env の自動読み込み:
- プロジェクトルートを .git または pyproject.toml で検出して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env.local は既存キーを上書きします（ただし OS の環境変数は保護されます）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

概要的にパッケージ内の主なファイル / モジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（ai_scores 生成）
    - regime_detector.py          — マクロ + MA200 を組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント・save/fetch 実装
    - pipeline.py                 — ETL パイプライン、run_daily_etl 等
    - etl.py                      — ETLResult のエクスポート
    - news_collector.py           — RSS 収集・前処理・raw_news 保存
    - quality.py                  — データ品質チェック
    - calendar_management.py      — market_calendar / 営業日ユーティリティ
    - stats.py                    — zscore_normalize 等
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — momentum / value / volatility の計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー等

（上記は主要モジュールのみ抜粋。細かいユーティリティは各ファイル内に実装されています）

---

## 運用上の注意・設計上のポイント

- ルックアヘッドバイアス防止:
  - AI モジュールや ETL は内部で datetime.today()/date.today() を無造作に使わない（target_date を明示的に渡す設計）。
  - prices_daily などのクエリは target_date 未満 / 以前の条件で過去データのみを使用するよう配慮されています。

- 冪等性:
  - J-Quants からの保存（save_*）は ON CONFLICT DO UPDATE を利用して冪等に保存します。
  - ETL は差分取得＋バックフィル（デフォルト 3 日）で後出し修正を吸収します。

- API 呼び出しの堅牢化:
  - J-Quants: レート制御（120 req/min）の固定間隔スロットリング、指数バックオフ、401 時のトークンリフレッシュ。
  - OpenAI: レスポンスの検証、429/ネットワーク/5xx のリトライ、JSON モードの利用。

- セキュリティ:
  - RSS 取得時はリダイレクト先のスキーム/ホストチェック（SSRF 防止）・受信サイズ制限・defusedxml を利用した安全な XML パースを行います。
  - URL 正規化によるトラッキングパラメータ除去（記事ID の安定化）を実施。

---

## 開発 / 貢献

- 型注釈、ロギング、単体テスト可能な分離（外部 API 呼び出し部分を差し替えやすい実装）に留意しています。  
- テストを書くときは network / API 呼び出し部分（jquants_client._request や news_nlp._call_openai_api など）をモックしてください。
- 大きな変更を行う場合はルックアヘッドバイアスや冪等性を損なわないよう注意してください。

---

README に書かれている操作例や環境変数はコード内の実装に基づくものです。実運用前にローカル環境で少量データに対する動作確認を行い、必要な API キーや DB のバックアップ方針等を整えてください。