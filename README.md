KabuSys
=======

KabuSys は日本株のデータパイプライン、特徴量計算、ニュース NLP、マーケットレジーム判定、および監査ログ管理を目的としたライブラリ群です。主に DuckDB をデータストアとして使い、J-Quants API や RSS 等からデータを取り込み、ETL・品質チェック・AI（OpenAI）を使ったニュースセンチメント評価・リサーチ用のファクター計算を提供します。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）の自動差分取得と保存
- ニュースの収集・前処理・LLM による銘柄センチメント付与（ai_scores）
- マーケットレジーム判定（ETF + マクロニュースの統合スコア）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ

機能一覧
- data
  - ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（fetch/save の完全実装、トークンリフレッシュ・レート制御・リトライ）
  - news_collector（RSS 収集・前処理・SSRF 対策・gzip 上限）
  - calendar_management（営業日判定・next/prev_trading_day・calendar_update_job）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査テーブル DDL / 初期化 / init_audit_db）
  - stats（zscore_normalize）
- ai
  - news_nlp.score_news（ニュース集約→OpenAI 呼び出し→ai_scores 保存）
  - regime_detector.score_regime（1321 の MA + マクロニュースの LLM センチメントを合成して market_regime を更新）
  - LLM 呼び出しは OpenAI Python SDK を想定（gpt-4o-mini を利用）
- research
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（.env 自動ロード、必須設定チェック、KABUSYS_ENV / LOG_LEVEL 等）
- その他
  - data.audit: 監査スキーマ定義と初期化関数（DuckDB 用）

前提条件
- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必要なパッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (macOS/Linux)
   - .venv\Scripts\activate     # (Windows)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数（.env）
自動でプロジェクトルートの .env, .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主な環境変数:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

認証／API
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で参照）
- KABU_API_PASSWORD: kabuステーション API のパスワード（当該機能を使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

データベースパス（デフォルト値あり）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

システム設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

参考の .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

基本的な使い方（短いコード例）
- DuckDB に接続して日次 ETL を回す例

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
# 日次 ETL を実行（target_date を指定するか省略して今日を使う）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを評価して ai_scores を書き込む例

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")

- 市場レジームを判定して書き込む例

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19), api_key=None)

- 監査ログ DB 初期化（別 DB として使う例）

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後、この conn_audit に対して監査レコードの INSERT/SELECT を実行

注意点 / 実運用での留意事項
- OpenAI 呼び出し: API 制限やエラーに対してリトライ・フェイルセーフ設計になっていますが、利用料やスロットリングに注意してください。score_news / score_regime は API キーを引数で注入可能（テスト容易化のため）。
- Look-ahead bias の回避: コード内の多くの関数は date 引数を受け取り、内部で datetime.today() を参照しないよう設計されています。バックテストや再現性に配慮してください。
- DuckDB executemany の挙動: 一部の関数は DuckDB のバージョン依存性（executemany に空リスト渡せない等）に配慮した実装になっています。DuckDB の互換性に注意してください。
- news_collector: RSS を取得する際に SSRF 対策や最大受信サイズチェック、gzip 解凍上限などの安全設計があります。外部 URL の扱いには注意してください。
- 環境変数自動ロード: パッケージ import 時にプロジェクトルートを探索して .env を読み込みます（.git または pyproject.toml を根拠）。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult の定義 / 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research (エクスポート用の __init__ に各種関数をまとめている)
- （将来的に strategy / execution / monitoring などのモジュールが想定されています）

開発・テスト
- 単体テストやモックを利用する際、OpenAI 呼び出しやネットワーク I/O は差し替え可能（モジュール内の _call_openai_api や _urlopen 等を patch する設計になっています）。
- 環境変数自動読み込みはテストの前に無効化することを推奨します:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

貢献・拡張案
- strategy / execution / monitoring モジュールの追加（本体はデータ・研究レイヤーが整ってからの実装想定）
- CI 上での ETL 回帰テスト（小さいフェイク DB を用いたエンド・ツー・エンド）
- メトリクス収集とアラート（Prometheus / Grafana / Slack 通知の統合）

ライセンス
- （ここにプロジェクトのライセンス表記を入れてください）

問い合わせ
- 実装に関する質問や不明点はリポジトリの Issues へご記入ください。

以上。README の記載や例で補足が必要であれば、使用したいワークフロー（ETL の自動化、バックテスト統合、監査ログの利用方法等）を教えてください。それに合わせた使い方例や追加ドキュメントを作成します。