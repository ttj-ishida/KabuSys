KabuSys
======

日本株向けのデータ基盤・研究・AI/戦略ユーティリティ群をまとめたライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・LLM によるニュースセンチメント、ファクター計算、マーケットカレンダー管理、監査ログ（注文→約定トレース）などの機能を提供します。

主な特徴
- J-Quants API から株価 / 財務 / カレンダーの差分 ETL を行い DuckDB に保存
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）・市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- 環境変数による設定管理（.env 自動ロード機能あり）

目次
- プロジェクト概要
- 機能一覧
- 要求環境 / 依存ライブラリ
- セットアップ手順
- 環境変数（主なもの）
- 使い方（簡単な使用例）
- ディレクトリ構成

プロジェクト概要
---------------
KabuSys は、日本株の自動売買やリサーチ用途に使える共通基盤ライブラリ群です。  
データ収集（J-Quants）、前処理、品質チェック、AI によるニュース評価、ファクター計算、監査ログなどをモジュール化して提供します。  
Look-ahead bias を避ける設計が各所に盛り込まれており、本番運用（live）とペーパー運用（paper_trading）、開発（development）を環境切替で扱えます。

機能一覧
---------
- データ取得 / ETL
  - J-Quants からの株価（daily_quotes）、財務（statements）、上場情報、マーケットカレンダー取得（fetch_*）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース
  - RSS 取得と前処理（SSRF 対策、URL 正規化、トラッキング除去）
  - ニュース→銘柄紐付け、raw_news 保存
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
- AI（市場レジーム判定）
  - ETF (1321) の MA 比率とマクロニュースを合成し日次で market_regime を生成（score_regime）
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算（calc_forward_returns）、IC 計算、統計サマリー、Z スコア正規化
- データ品質チェック（quality.run_all_checks）
  - 欠損／スパイク／重複／日付不整合検出
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル作成ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env ファイルまたは環境変数から各種設定を読み込み（kabusys.config.settings）
  - 自動 .env ロード（プロジェクトルート検出）を提供（無効化フラグあり）

要求環境 / 依存ライブラリ
-----------------------
- Python 3.10+
  - 型注釈の表記に | を使用しているため Python 3.10 以降を想定しています
- 主な Python パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- その他（用途に応じて）
  - requests 等（本コードでは urllib を使用しているため必須ではない）
- 推奨: 仮想環境（venv / virtualenv / conda）

セットアップ手順
----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布で setup.py / pyproject.toml があれば pip install -e . を使用してください）

3. 環境変数 (.env) を用意
   - プロジェクトルートに .env を置くと自動ロードされます（.git または pyproject.toml がある親ディレクトリを探索）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要なディレクトリを作成（例）
   - mkdir -p data

環境変数（主なもの）
-------------------
以下は main な設定キーです（必須のものは README 内で明記します）。

必須（アプリの一部機能で必須）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL 実行に必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime を実行する場合に必須）
- KABU_API_PASSWORD：kabu ステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID：Slack 通知を行う場合に使用

任意（デフォルト値あり）
- KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
- LOG_LEVEL：DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL：kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

簡易 .env.example
-----------------
例（プロジェクトルートに .env として保存）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な呼び出し例）
-------------------------

準備: DuckDB 接続と settings の利用例
- Python REPL / スクリプト内で:

from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB ファイルに接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

ETL 実行（日次）
- 日次 ETL を実行してデータを取得・保存・品質チェックを行う:

from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニュース NLP（OpenAI）によるスコア付与
- raw_news / news_symbols が整備されている前提で:

from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n}")

市場レジーム判定（MA + マクロニュース）
- ETF(1321) の MA200 乖離とマクロニュースを合成して market_regime に書き込む:

from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))

監査 DB 初期化
- 監査ログ専用の DuckDB を作成して初期化する:

from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます

研究用ファクター計算
- calc_momentum 等を呼び出してファクターを取得:

from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))

データ品質チェック
- run_all_checks で各種品質チェックを実行:

from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)

注意点 / 設計思想（抜粋）
------------------------
- Look-ahead bias の防止:
  - 各種スコアリング・ETL は内部で date を明示的に受け取り、datetime.today() を参照しない設計になっています。
  - prices_daily 等のクエリでは target_date 未満などの排他条件を用いています。
- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等にしています。
- フェイルセーフ:
  - LLM 呼び出しや外部 API エラー時は「スコアを 0 にフォールバック」するなど、致命的でない限り処理は継続します。
- セキュリティ:
  - RSS 取得には SSRF 対策（リダイレクト先検査 / プライベート IP 拒否）を行っています。
  - XML 解析には defusedxml を使用して XML Bomb 等を回避しています。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュール一覧と役割の簡単な説明です。

- kabusys/
  - __init__.py
  - config.py                : 環境変数 / .env 自動ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py            : ニュースの LLM スコアリング（score_news）
    - regime_detector.py     : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py : マーケットカレンダー管理・営業日判定
    - etl.py                 : ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - stats.py               : 統計ユーティリティ（zscore_normalize）
    - quality.py             : データ品質チェック
    - audit.py               : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - jquants_client.py      : J-Quants API クライアント（fetch / save）
    - news_collector.py      : RSS 取得・記事正規化・保存ロジック
  - research/
    - __init__.py
    - factor_research.py     : モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー
  - monitoring/               : （監視・運用）※実装ファイルが本リポジトリにあればここに
  - strategy/                 : 戦略層（シグナル生成等）※実装ファイルが本リポジトリにあればここに
  - execution/                : 発注 / ブローカー連携（kabu 等）※実装ファイルが本リポジトリにあればここに

付記: ソースコードの大部分はデータ取得・前処理・品質管理に関する堅牢なユーティリティで構成されており、戦略や発注ロジックは別途実装して本モジュールを組み合わせて使う想定です。

ライセンス / 貢献
-----------------
本リポジトリに含まれるコードの利用条件・ライセンスはリポジトリの LICENSE ファイルを参照してください。  
バグレポート・改善提案は Issue / Pull Request を通じて歓迎します。

お問い合わせ
------------
使い方や実装上の疑問点があれば、README を管理しているリポジトリの Issue またはリポジトリ管理者へお問い合わせください。