KabuSys — 日本株自動売買／データプラットフォーム
==================================================

概要
----
KabuSys は日本株のデータパイプライン・特徴量探索・ニュース NLP・市場レジーム判定・監査ログなどを備えた自動売買／リサーチ基盤のライブラリ群です。  
主に以下を提供します：

- J-Quants API 経由の株価・財務・市場カレンダー ETL（差分取得・バックフィル・品質チェック）
- RSS ニュース収集と OpenAI を用いた銘柄センチメント（ai_scores）生成
- マクロセンチメントと ETF MA を合成した日次市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）および特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマ初期化・管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）

主な設計方針
- ルックアヘッドバイアスを避ける（target_date を明示、date.today() を内部で参照しない箇所が多い）
- DuckDB をデータ層に採用、ETL は idempotent（ON CONFLICT）で実装
- 外部 API 呼び出しにはリトライ・バックオフ・レート制御を実装
- OpenAI 呼び出しは JSON モードで厳密なレスポンスを期待し、失敗時はフェイルセーフで継続

機能一覧
---------
- data.jquants_client: J-Quants API ラッパー（取得・保存・認証・レート制御）
- data.pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data.quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- data.news_collector: RSS 収集・前処理・raw_news 登録（SSRF 対策・トラッキング除去・サイズ制限）
- ai.news_nlp: ニュースをまとめて OpenAI で銘柄ごとのセンチメントを算出（score_news）
- ai.regime_detector: ETF(1321)の MA200 乖離とマクロセンチメントを合成して market_regime を算出（score_regime）
- research.*: ファクター計算（calc_momentum, calc_value, calc_volatility）・特徴量解析（calc_forward_returns, calc_ic, factor_summary）・zscore_normalize 等
- data.audit: 監査ログスキーマ初期化ユーティリティ（init_audit_schema / init_audit_db）
- config: 環境変数読み込みと Settings（.env 自動ロード、必須キーチェック）

前提 / 必要環境
----------------
- Python 3.10+（型アノテーションで Union | などを使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

インストール（開発用）
--------------------
リポジトリルートで仮想環境を作成し、必要パッケージをインストールしてください（requirements.txt は含まれていない想定のため、下記は一例です）。

例:
1. 仮想環境作成
   python -m venv .venv
   source .venv/bin/activate

2. インストール（開発）
   pip install -e .    # setup.py / pyproject があれば開発インストール
   pip install duckdb openai defusedxml

注: 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

設定（環境変数 / .env）
---------------------
config.Settings により .env ファイル（プロジェクトルート）または環境変数から設定を自動読み込みします（優先度: OS 環境 > .env.local > .env）。

自動読み込みを無効にする:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な必須環境変数
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（ETL の認証に使用）
- KABU_API_PASSWORD      — kabu ステーション API 用パスワード（実行モジュールがある場合に使用）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID       — Slack チャンネル ID
- OPENAI_API_KEY         — OpenAI API キー（ai.score_news / regime_detector で必要）

その他（省略可）
- KABUSYS_ENV            — "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH            — デフォルト data/kabusys.duckdb
- SQLITE_PATH            — 監視 DB のデフォルト data/monitoring.db

簡易 .env.example（参考）
-------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

使い方（Quickstart）
-------------------

1) DuckDB 接続を用意する
例:
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

（必要に応じてスキーマ初期化などはプロジェクト側で行ってください）

2) 日次 ETL を実行する
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ETL は市場カレンダー→株価→財務→品質チェックの順で実行します。
- J-Quants の認証は settings.jquants_refresh_token を使って自動取得します。必要なら id_token を引数で注入できます。

3) ニュースセンチメント（銘柄単位）を算出する
from datetime import date
from kabusys.ai.news_nlp import score_news
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None は OPENAI_API_KEY を参照
print(f"scored {n} codes")

4) 市場レジームを算出する（ETF 1321 の MA200 乖離 + マクロセンチメント）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 監査ログ DB 初期化（監査専用 DB）
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査スキーマ初期化済みの DuckDB 接続

API の主な戻り値 / 副作用
- data.pipeline.run_daily_etl → ETLResult（取得数・保存数・quality_issues・errors 等を含む）
- ai.news_nlp.score_news → 書き込んだ銘柄数（ai_scores テーブルへ）
- ai.regime_detector.score_regime → 1（成功時）および market_regime テーブルへ書き込み

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py            - パッケージ初期化（version 等）
- config.py              - 環境変数/.env 読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py          - ニュース NLU / OpenAI 呼び出し・スコアリング（score_news）
  - regime_detector.py   - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    - J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py          - ETL パイプライン（run_daily_etl 等）
  - etl.py               - ETLResult の再エクスポート
  - news_collector.py    - RSS 収集・前処理
  - calendar_management.py - 市場カレンダーロジック（is_trading_day 等）
  - quality.py           - データ品質チェック
  - stats.py             - 汎用統計（zscore_normalize）
  - audit.py             - 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py   - ファクター計算（momentum/value/volatility）
  - feature_exploration.py - 将来リターン・IC・統計サマリー等

注意事項 / 運用メモ
------------------
- OpenAI 呼び出しは課金対象かつレート要件があるので本番ではキー管理とレート監視を行ってください。
- ETL・API 呼び出し部分はリトライやフェイルセーフを備えていますが、長時間失敗するとデータ欠損や遅延が発生します。監視を設定してください（Slack 等）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany などの内部実装はバージョン依存の挙動を考慮しています（空リストでの executemany 回避など）。

貢献 / 拡張
------------
- 新しい ETL ソースやモデルを追加する場合は data.jquants_client を参考に、idempotent な保存（ON CONFLICT）と取得時の fetched_at を忘れずに実装してください。
- AI 関連は _call_openai_api をモックしてユニットテストを書くことで安定したテストが行えます。

ライセンス
----------
本リポジトリにライセンスファイルがない場合は、利用・配布に関してプロジェクトポリシーに従ってください。

問題報告 / 問い合わせ
--------------------
バグ報告や質問は Issue を作成してください。README にない実装上の意図（ルックアヘッド回避・フェイルセーフ等）はソース内コメントを参照してください。

以上。必要なら README にサンプル .env.example や requirements.txt、CI / テスト実行手順を追加します。どの情報を追記しますか？