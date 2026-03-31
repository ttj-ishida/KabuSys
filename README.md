KabuSys
======

概要
----
KabuSys は日本株のデータ収集・前処理・特徴量生成・市場レジーム判定・ニュースNLPスコアリング・監査ログ管理を目的としたライブラリ群／パイプラインです。  
主に以下を提供します：

- J-Quants API 経由の株価・財務・マーケットカレンダーの差分 ETL（DuckDB に保存）
- ニュース収集（RSS）と銘柄別の NLP センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアの合成）
- 研究用のファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量探索ユーティリティ
- 監査ログ（signal → order → execution）のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）

主な設計方針は「Look-ahead bias を避ける」「冪等（idempotent）」「外部 API 呼び出しに対する堅牢なリトライ/フェイルセーフ」です。

主な機能
--------
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- J-Quants クライアント: 認証・ページネーション・レート制御・保存ユーティリティ（kabusys.data.jquants_client）
- News Collector: RSS 取得・正規化・SSRF 対策・前処理・raw_news への保存（kabusys.data.news_collector）
- News NLP: 銘柄別ニュースをまとめて OpenAI（gpt-4o-mini）で評価し ai_scores に保存（kabusys.ai.news_nlp）
- Regime Detector: ETF 1321 とマクロニュースを合成して market_regime に保存（kabusys.ai.regime_detector）
- Research: ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリ（kabusys.research）
- Data utilities: calendar 管理、quality チェック、stats（zscore 等）、audit スキーマ初期化（kabusys.data）
- 設定管理: .env 自動ロード / 環境変数ラッパー（kabusys.config.Settings）

セットアップ
-----------
1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール（プロジェクトの requirements.txt / pyproject.toml がある場合はそれを使用）

例（最低限想定される主要依存）:
- duckdb
- openai
- defusedxml

pip 例:
pip install duckdb openai defusedxml

パッケージを開発モードでインストール:
pip install -e .

環境変数 / .env
----------------
kabusys は .env/.env.local をプロジェクトルートから自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み優先度は OS 環境変数 > .env.local > .env です。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が ID トークンを取得するため）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で使用する想定）
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能がある場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意／デフォルト値あり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 sqlite データベース（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

使い方（コード例）
-----------------

- DuckDB 接続を使った日次 ETL 実行（例）:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP スコア生成:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

- 市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を参照

- 監査ログ DB 初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))

運用上のポイント
----------------
- Look-ahead バイアス回避: モジュールの多くは内部で date を明示的に受け取り、datetime.today() を参照しない設計です。バックテスト/再現性を保つため、常に明示的な target_date を渡すことを推奨します。
- 冪等性: ETL・保存関数は ON CONFLICT / idempotent に設計されているため、再実行による重複データ発生を抑制できます。
- API 呼び出し: J-Quants / OpenAI はリトライ・レート制御を実装していますが、APIキーやレート制限の管理は運用側で行ってください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。CI／テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD をセットするか明示的に環境変数を渡してください。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（銘柄別スコア生成）
  - regime_detector.py            — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存ロジック
  - pipeline.py                   — ETL パイプラインと run_daily_etl
  - etl.py                        — ETLResult のエクスポート
  - news_collector.py             — RSS 収集・前処理
  - calendar_management.py        — 市場カレンダー管理ユーティリティ
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
  - quality.py                    — データ品質チェック群
  - audit.py                      — 監査ログスキーマの初期化
- research/
  - __init__.py
  - factor_research.py            — momentum/value/volatility 等
  - feature_exploration.py        — forward returns, IC, summary
- ai/ (既述)
- research/ (既述)

各モジュールの目的（簡潔）
- config: .env のパース、自動ロード、Settings クラスでアプリ設定をラップ
- data.jquants_client: API 通信、ページネーション、保存（raw_prices, raw_financials, market_calendar 等）
- data.pipeline: 差分取得・保存の上位エントリポイント（run_daily_etl 等）
- data.news_collector: RSS 取得、SSRF 対策、記事正規化、raw_news への保存
- ai.news_nlp / ai.regime_detector: OpenAI を使ったスコアリングとレジーム合成
- research: 研究／バックテスト用のファクター計算・統計関数
- data.quality: ETL 後の品質検査を一括実行するユーティリティ
- data.audit: 発注/約定を追跡する監査テーブルの DDL と初期化ユーティリティ

開発・テスト
-------------
- 環境変数を .env.example を元に作成してください（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）。
- 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境を自前で用意してください。
- OpenAI 呼び出し等はユニットテストではモック（patch）することを想定しています（各モジュールに _call_openai_api 等の差し替えポイントあり）。

補足
----
- この README はソースコードの主要機能と使い方の概要を示します。API の詳細やスキーマ（テーブル定義／カラム一覧）はソースファイル内の docstring を参照してください。各関数は docstring により引数・戻り値、設計上の注意点が明記されています。