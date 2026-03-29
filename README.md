# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・LLM を用いたニュースセンチメント・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤とデータパイプラインを構築するためのライブラリ群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース RSS の収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメントとの合成による市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用のスキーマと初期化ユーティリティ

設計上、ルックアヘッドバイアスの防止、冪等処理（ON CONFLICT 等）、外部 API のリトライやフェイルセーフが組み込まれています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_*/save_*、認証、レート制御、リトライ）
  - ニュース収集（RSS 取得・前処理・SSRF 対策・記事ID生成）
  - カレンダー管理（営業日判定・next/prev trading day・calendar_update_job）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査用テーブルとインデックスの作成）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI でスコア化して ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを合成して market_regime を作成
- research/
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ、ランク関数など
- config: .env 自動読み込み（プロジェクトルート検出）、環境設定ラッパー

---

## 必要条件 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- （標準ライブラリのみで実装されている機能も多いです）

requirements.txt がない場合は最低限次をインストールしてください（プロジェクトに合わせて調整してください）:

pip install duckdb openai defusedxml

注: 実環境では他の依存（Slack SDK など）を追加することがあります。

---

## セットアップ手順

1. リポジトリをクローン（例）

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール

   pip install -U pip
   pip install -e ".[dev]"     # プロジェクトが setuptools/pyproject を持つ場合
   # または最低限:
   pip install duckdb openai defusedxml

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。必要なキー例:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）データベースパス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の書式は一般的な KEY=VALUE で、コメントや export 付きもある程度対応します。

---

## 使い方（主要ユースケースの例）

以下は最小限の使用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続を準備し ETL を実行する（日次 ETL）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- News NLP（銘柄別ニュースセンチメントを作成）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", num_written)

  - 引数 `api_key` に OPENAI_API_KEY を渡すことも可能（省略時は環境変数 OPENAI_API_KEY を使用）。

- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # 戻り値は 1（成功）

- 監査ログ用 DB 初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn に対して監査テーブルが利用可能

- カレンダーヘルパーの利用例

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import (
      is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  )

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(prev_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))

- 研究用ファクター計算

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  # conn は DuckDB 接続、target_date は分析対象日
  momentum = calc_momentum(conn, target_date)
  volatility = calc_volatility(conn, target_date)
  value = calc_value(conn, target_date)

注意:
- OpenAI 呼び出しは API レート・課金対象になります。テストではモックを利用してください。
- ETL / OpenAI 呼び出し時のリトライ・フェイルセーフが実装されていますが、API キーやネットワークが未設定だと例外が上がります。

---

## 推奨ワークフロー / 運用メモ

- 本番での env 設定は .env.local（機密）を利用し .env はサンプル化する運用を推奨します。
- KABUSYS_ENV を `live` にするとライブ向けフラグが立ちます。`paper_trading` も利用可能です。
- OpenAI 呼び出し失敗時はニュース/レジーム処理はスコア 0.0 をフォールバックして継続する実装になっています（フェイルセーフ）。
- ETL は夜間バッチで定期実行し、calendar_update_job を先に回すと営業日調整が安定します。
- テスト時に自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境設定 / .env 自動読み込み
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（OpenAI）
  - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch / save / auth）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETL の公開型再エクスポート
  - news_collector.py             — RSS 収集と前処理（SSRF 対策等）
  - calendar_management.py        — マーケットカレンダー管理
  - quality.py                    — データ品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            — モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ
- monitoring/ (パッケージは __all__ に含まれる想定: 実装ファイルがあれば監視用コード)
- strategy/ (戦略レイヤー想定)
- execution/ (発注実装想定)

（実際のリポジトリでは上記以外にドキュメント・テスト・CI 設定が存在する場合があります）

---

## よくあるトラブルシューティング

- 環境変数が足りない:
  - config.Settings が必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を参照すると ValueError を出します。`.env.example` を参考に設定してください。
- OpenAI が動かない:
  - OPENAI_API_KEY が未設定のときは score_news / score_regime が ValueError を投げます。テストでは api_key 引数にダミー値を渡し内部呼び出しをモックしてください。
- DuckDB ファイルの書き込みパーミッション:
  - デフォルトの `data/kabusys.duckdb` の親ディレクトリを作成・書き込み権限を確認してください。
- ネットワーク・API 呼び出し不安定:
  - jquants_client / news_nlp / regime_detector にはリトライ・バックオフがあります。長時間失敗する場合は API キー・ネットワーク・IP ホワイトリスト等を確認してください。

---

## テスト・開発

- ユニットテストでは OpenAI 呼び出し・ネットワークアクセスをモックすることを推奨します（コード内に unittest.mock.patch を利用するための差し替えポイントが用意されています）。
- 自動 .env ロードを無効にしてテスト環境を安定化させるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

以上が KabuSys の概要・セットアップ・利用方法のガイドです。  
さらに詳しい API や設計文書（DataPlatform.md / StrategyModel.md 等）が存在する場合は、それらを参照して運用・実装を進めてください。必要であれば README に追加したい具体的なコマンドやサンプルを教えてください。