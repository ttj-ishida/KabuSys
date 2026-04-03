KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買支援ライブラリです。  
J-Quants からのデータ取得・ETL、ニュース収集と LLM を用いたニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）やマーケットカレンダー管理などを含むモジュール群を提供します。

主な特徴
--------
- データ取得・ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション・トークン自動リフレッシュ・レートリミット対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集・NLP
  - RSS からニュースを取得して正規化・保存、SSRF 対策や受信サイズ制限等の安全対策あり
  - OpenAI（gpt-4o-mini 等）を使った銘柄別ニュースセンチメント（ai_scores）とマクロセンチメント（market_regime）算出
- 研究（Research）ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC（Information Coefficient）、統計サマリーなど
- 監査（Audit）ログ
  - signal → order_request → executions のトレーサビリティを保持する監査テーブル定義・初期化機能
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルート検出ベース）。自動ロード無効化フラグあり。

セットアップ手順
----------------

前提
- Python 3.10 以上（ソースは union 型 A | B を使用）
- システムに duckdb、openai 等がインストールできること

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表的なパッケージ）
   - pip install duckdb openai defusedxml

   必要に応じて他のユーティリティ（例: requests）を追加してください。

3. パッケージのインストール（開発時）
   - リポジトリルートに pyproject.toml があれば:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動的にロードされます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須または主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（既定: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)（既定: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

サンプル .env（最低限の例）
（実運用では秘密情報を適切に管理してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXX
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的な使い方（コード例）
-------------------------

1) DuckDB 接続と日次 ETL 実行
- 日次 ETL は prices / financials / calendar の差分取得と品質チェックを行います。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースのセンチメント算出（ai_scores へ書き込み）
- OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡します。

例:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str("/path/to/your.duckdb"))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数から取得
print("書き込み銘柄数:", n_written)

3) マクロ + MA200 を使った市場レジーム判定（market_regime テーブルへ書き込み）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str("/path/to/your.duckdb"))
score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査ログデータベースの初期化
- 監査用の DuckDB を初期化して監査テーブルを作成します。

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等が作成されます

5) 研究向けファクター計算
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))

各モジュールのポイント
---------------------
- kabusys.config
  - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を探索）
  - settings オブジェクト経由で設定取得（必須キーは _require により ValueError を投げる）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 内部で RateLimiter とリトライを備える

- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL の統合エントリポイント。ETLResult を返す

- kabusys.data.news_collector
  - fetch_rss 等。SSRF 対策・XML パースは defusedxml を使用

- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - OpenAI（gpt-4o-mini 想定）を用いたニュース・マクロセンチメント評価
  - API リトライ（429/ネットワーク/5xx）やレスポンスバリデーションを実装
  - Look-ahead バイアス対策: target_date 未満/前日ウィンドウのみ参照

- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary 等
  - zscore_normalize は kabusys.data.stats で提供

- kabusys.data.quality
  - 各種品質チェックを実装。QualityIssue のリストを返す

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                : パッケージ初期化、バージョン
- config.py                  : 環境設定管理（.env 自動読み込み・settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py              : ニュースセンチメント算出（ai_scores に書き込み）
  - regime_detector.py       : マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py        : J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py              : ETL パイプラインと run_daily_etl
  - etl.py                   : ETLResult エクスポート
  - news_collector.py        : RSS 取得・前処理・保存
  - calendar_management.py   : マーケットカレンダー・営業日ロジック
  - stats.py                 : zscore_normalize 等の統計ユーティリティ
  - quality.py               : データ品質チェック
  - audit.py                 : 監査ログテーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py       : ファクター計算（mom, value, volatility）
  - feature_exploration.py   : 将来リターン・IC・統計サマリー等
- monitoring/ (存在する場合: 監視・実行制御系)
- execution/  (存在する場合: 発注・実行ロジック)
- strategy/   (存在する場合: 戦略定義)

注意事項・運用上のヒント
-----------------------
- OpenAI や J-Quants の API キーは機密情報です。ソース管理には直接置かず、環境変数や安全なシークレットマネージャを使用してください。
- ETL と AI の呼び出しは API レート・コストに注意して運用してください（OpenAI の呼び出しはバッチ化・制限を推奨）。
- DuckDB はスキーマ設計（主キー・インデックス）に依存する処理があるため、スキーマが正しく初期化されていることを確認してください（audit.init_audit_db 等）。
- テスト時は環境読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を活用すると良いです。
- モジュールの一部はテスト時に内部 API 呼び出し関数をモックすることを想定した設計（例: _call_openai_api をモック）になっています。

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。必要に応じて LICENSE を追加してください。）

問い合わせ・開発
----------------
バグ報告や機能追加の提案はリポジトリの Issue を利用してください。開発時はユニットテストを追加し、API キーを使わないモック/スタブでテスト可能な設計を推奨します。