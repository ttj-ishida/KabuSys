# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・AI による記事センチメント評価、ファクター計算、マーケットレジーム判定、監査ログ（発注→約定トレーサビリティ）などを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ環境向けに設計された Python パッケージです。  
主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価（銘柄単位・マクロ）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 市場レジーム判定（ETF・MA とマクロニュースを合成）
- 監査ログ（signal → order_request → execution の永続化）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴として、ルックアヘッドバイアス防止（日時を勝手に参照しない）、DuckDB を使った高速かつ冪等な保存、外部 API 呼び出しのリトライ/レート制御、セキュリティ配慮（SSRF 対策、XML の安全なパース）などが組み込まれています。

---

## 機能一覧

- data/
  - ETL pipeline（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - calendar management（営業日判定、next/prev_trading_day、calendar_update_job）
  - news_collector（RSS 取得・前処理・raw_news 保存）
  - quality（データ品質チェック）
  - audit（監査ログテーブル作成・初期化）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)
    - ニュースを銘柄単位にまとめ、OpenAI に渡して ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
- research/
  - factor_research (calc_momentum, calc_value, calc_volatility)
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
- config
  - Settings: 環境変数から設定を取得（J-Quants トークン、kabu API、Slack、DB パスなど）
  - 自動 .env ロード（プロジェクトルートを基準に .env, .env.local を読み込み。無効化可）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存パッケージ（例）
- duckdb
- openai
- defusedxml

実際のインストール要件はプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン／取得する

   git clone ... （または適切にソースを配置）

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. パッケージのインストール（開発用）

   pip install -e .

   依存が別途ある場合:
   pip install duckdb openai defusedxml

4. 環境変数 / .env の準備

   プロジェクトルート（.git または pyproject.toml がある階層）に `.env` として以下を設定してください。

   例（.env.example）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=＜your_jquants_refresh_token＞

   # kabu ステーション
   KABU_API_PASSWORD=＜your_kabu_api_password＞
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI (news scoring / regime detector に必要)
   OPENAI_API_KEY=＜your_openai_api_key＞

   # Slack (通知など)
   SLACK_BOT_TOKEN=＜your_slack_bot_token＞
   SLACK_CHANNEL_ID=＜your_slack_channel_id＞

   # 環境 / ログ
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   自動 .env 読み込みはデフォルトで有効です。自動ロードを無効化する場合は
   `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB ファイルの作成（必要に応じて）

   デフォルトの DB パスは `data/kabusys.duckdb` です。初期化スクリプトで監査テーブル等を作成できます（下記参照）。

---

## 使い方（サンプル）

以下はパッケージの主要な機能を呼び出すためのサンプルコードです。各関数は DuckDB の接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取ります。

- ETL を日次実行する（run_daily_etl）

  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を渡さなければ今日が対象（ただし内部で調整あり）
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores に書き込む

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に入れておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
  ```

- 市場レジーム（bull/neutral/bear）を判定して保存する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（audit）スキーマを初期化する（監査用 DB または メイン DB に作成）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_kabusys.duckdb")  # または ":memory:"
  # init_audit_db はテーブル作成まで実行し、DuckDB 接続を返す
  ```

- ファクター計算・研究関数の使用例

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  forward = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 設定の参照

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- OpenAI API を呼ぶ機能（news_nlp, regime_detector）は API キーが必要です。環境変数 `OPENAI_API_KEY` を設定するか、関数引数 `api_key` を渡してください。
- DuckDB の操作はトランザクションで保護されていますが、呼び出し側のトランザクション管理にも注意してください（モジュール内で BEGIN/COMMIT/ROLLBACK を行う関数があります）。
- ETL / API 呼び出しはネットワークリトライやレート制御を行っていますが、API キー・ネットワークの制限にご注意ください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py           # ニュースのセンチメント評価と ai_scores 書き込み
  - regime_detector.py    # 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - pipeline.py           # ETL パイプライン（run_daily_etl 等）
  - jquants_client.py     # J-Quants API クライアント（fetch / save）
  - news_collector.py     # RSS ニュース収集・前処理
  - quality.py            # データ品質チェック
  - calendar_management.py# 市場カレンダー管理（営業日判定など）
  - audit.py              # 監査ログテーブル定義・初期化
  - stats.py              # 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py           # ETLResult クラス / run_daily_etl など
  - etl.py (再エクスポート)
- research/
  - __init__.py
  - factor_research.py    # モメンタム / バリュー / ボラティリティ
  - feature_exploration.py# 将来リターン, IC, 統計サマリー
- research/__init__.py
- その他モジュール（execution, monitoring, strategy 等はパッケージに含まれる場合あり）

（上記はリポジトリ内の主要ファイルを抜粋したものです。実際のツリーはリポジトリを参照してください。）

---

## 設定・環境変数（主なもの）

必須（機能により必須）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD      — kabu ステーション API パスワード（発注に使用）
- SLACK_BOT_TOKEN        — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID       — Slack のチャネル ID

オプション / デフォルトあり:
- OPENAI_API_KEY         — OpenAI 呼び出しで利用（score_news / score_regime）
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 の場合 .env 自動読み込みを無効化

注意: settings のプロパティは必須変数未設定時に ValueError を送出するものがあります（必須トークンなど）。.env を整備してから実行してください。

---

## テストとデバッグについて

- AI モジュール内のネットワーク呼び出しは _call_openai_api の差し替え（モック）を想定しており、ユニットテストで簡単にモック可能です。
- news_collector の HTTP 呼び出しは _urlopen を差し替えてテストできます。
- 自動 .env ロードはテスト時にオフにすることができます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 運用上の注意

- LIVE 環境（KABUSYS_ENV=live）での実行は非常に注意してください。実際の発注ロジックを併用する場合、十分なテスト・モニタリングが必要です。
- OpenAI 呼び出しはコストがかかります。バッチ化や呼び出し頻度に注意してください（news_nlp は最大バッチサイズ制御済み）。
- J-Quants API のレート制限を遵守する実装（固定間隔スロットリング）がありますが、他プロセスと共有する場合は調整が必要な可能性があります。

---

## ライセンス・貢献

このプロジェクトのライセンスや貢献方法はリポジトリルートの LICENSE / CONTRIBUTING ドキュメントを参照してください。

---

以上です。必要であれば README に含めたい追加の情報（CLI サンプル、Docker 構成、CI 設定、より詳細な .env.example 等）を教えてください。