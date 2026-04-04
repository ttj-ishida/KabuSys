# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレース）、市場カレンダー管理、品質チェックなど、アルゴリズム売買基盤で必要となる機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数 / .env
- ディレクトリ構成（概要）
- 設計上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームを構成するためのモジュール群です。主に以下の領域をカバーします。

- データ取得（J-Quants API）と DuckDB への保存（ETL）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック
- マーケットカレンダー管理（JPX）
- 監査ログ（シグナル→発注→約定のトレーサビリティを保証）
- 設定管理（.env / 環境変数の自動ロード）

設計方針として、バックテストでのルックアヘッドバイアスを避けるため「現在時刻を直接参照しない」などの注意点が各モジュールで反映されています。また、DuckDB をデータストアに用い、ETL は冪等的に動くよう実装されています。

---

## 主な機能（機能一覧）

- data.jquants_client
  - J-Quants API から株価 / 財務 / カレンダー等を取得し、DuckDB に保存（レートリミット・リトライ・トークン自動リフレッシュ対応）
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー、株価、財務の差分取得と品質チェック
- data.news_collector
  - RSS からニュースを収集し raw_news / news_symbols に保存（SSRF 防止、トラッキング除去、XML 安全化）
- ai.news_nlp
  - 銘柄別にニュースを集約して OpenAI（gpt-4o-mini）に送り、銘柄ごとの ai_score を ai_scores テーブルへ保存
- ai.regime_detector
  - ETF (1321) の 200 日移動平均乖離 + マクロニュースの LLM スコアを合成して日次の市場レジーム（bull/neutral/bear）を判定・保存
- research.factor_research, research.feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン計算、IC（スピアマン）等
- data.calendar_management
  - market_calendar を扱うユーティリティ（営業日判定、next/prev_trading_day、calendar_update_job）
- data.quality
  - 欠損、スパイク（急変）、重複、日付不整合の品質チェック群
- data.audit
  - signal_events / order_requests / executions など監査ログスキーマ定義と初期化ユーティリティ
- config
  - .env / 環境変数読み込み、アプリ設定ラッパー（settings）

重要な設計特徴:
- Look-ahead bias を避けるため、target_date を明示的に渡す（datetime.today() を直接参照しない）
- ETL / 保存処理は冪等性（ON CONFLICT 等）を考慮
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時はスキップや中立値で継続）

---

## セットアップ手順

以下は開発/実行のための基本手順です。

1. Python 環境（推奨: 3.10+）を用意
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt / poetry / pipx 等で管理してください。

3. ソースをプロジェクトに配置（例: pip install -e . など）
   - 開発時はリポジトリをクローンして src を Python パスに含めてください。

4. 環境変数設定
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.env.local があればそちらが優先して読み込まれます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB 等の初期化（監査DB 初期化例）
   - 監査ログ用 DB を初期化:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 環境変数 / .env 例

必須（実行する機能に応じて必要なものを設定してください）:

- JQUANTS_REFRESH_TOKEN=xxxxx      # J-Quants 用リフレッシュトークン（ETL）
- OPENAI_API_KEY=sk-...            # OpenAI（ニュース NLP / レジーム判定）
- KABU_API_PASSWORD=...            # kabuステーション API（注文実行等）
- (任意) KABU_API_BASE_URL=http://localhost:18080/kabusapi

DB パス（既定値あり）:
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

監視・PID 関連:
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0

システム設定:
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|... 

例 .env:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

注意:
- .env.local は .env を上書きするため、ローカルでの上書き値は .env.local に置くと良いです。
- 環境変数は OS 環境変数が優先されます。

---

## 使い方（簡単な例）

以下はライブラリを直接インポートして利用する際の簡単な利用例です。実行環境に合わせて必要な環境変数を設定してください。

1) DuckDB 接続を作って日次 ETL を実行する（J-Quants からの差分取得）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env 等から取得
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュース NLP（AI スコア）を実行する:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# target_date はスコアリング対象日（例: 今日）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Written {n_written} ai_scores")

3) 市場レジーム判定を行う:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

4) RSS を取得して raw_news に書き込む（news_collector.fetch_rss を活用）:
- news_collector には raw_news への永続化ロジックが含まれます（コード内関数を参照）。
- まず fetch_rss で記事を取得し、その後 DB に挿入するワークフローを行います。

5) 監査ログスキーマの初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions のテーブルが作成されます

注:
- OpenAI を使う機能（score_news, score_regime）は OPENAI_API_KEY が必要です。
- J-Quants を使う ETL は JQUANTS_REFRESH_TOKEN が必要です。
- 実運用での注文実行（kabuAPI 等）は別モジュール（execution）を使用予定ですが、API パラメータやパスワードは設定が必要です。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、settings オブジェクト
- ai/
  - __init__.py (score_news を re-export)
  - news_nlp.py         # ニュース NLP（銘柄別スコア）
  - regime_detector.py  # 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py  # market_calendar の管理・判定
  - etl.py                  # ETL の公開型（ETLResult）
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - stats.py                # zscore_normalize 等
  - quality.py              # データ品質チェック
  - audit.py                # 監査ログスキーマ初期化
  - jquants_client.py       # J-Quants API クライアント + 保存関数
  - news_collector.py       # RSS 取得 / 前処理
- research/
  - __init__.py
  - factor_research.py      # モメンタム / ボラティリティ / バリュー
  - feature_exploration.py  # 将来リターン / IC / 統計サマリ等
- research パッケージは data.stats を利用してファクター研究を支援
- その他: execution, monitoring, strategy 等のサブパッケージ（README に含めた核心モジュール群を中心に記載）

（上記は主要ファイルの抜粋です。実際のツリーはリポジトリをご参照ください。）

---

## 設計上の注意点 / 運用メモ

- Look-ahead Bias 対策
  - 多くの関数は target_date を引数で受け取り、内部で datetime.now() / date.today() を直接参照しないよう設計されています。バックテストや研究用途では必ず target_date を明示してください。
- 冪等性
  - ETL の保存処理は ON CONFLICT / UPDATE を用いて冪等性を担保しています（部分失敗時のデータ保全に配慮）。
- API の扱い
  - J-Quants は 120 req/min のレート制限を想定しており、モジュール内で固定間隔のスロットリングを実装しています。
  - OpenAI 呼び出しは JSON Mode を使用し、リトライやレスポンス検証を実施しています。API エラー時はフェイルセーフとして中立値（0.0）やスキップで継続する設計です。
- セキュリティ
  - news_collector では SSRF 対策（スキーム検証・プライベートIPブロック）、defusedxml による XML パースの安全化、レスポンスサイズ制限などを実装しています。
- テスト / モック
  - OpenAI 呼び出し等は内部関数をモックしやすいように切り出しがあり、ユニットテストで差し替え可能です（例: unittest.mock.patch を利用）。

---

必要に応じて README に追記します（実行スクリプト例、CI 設定、requirements.txt、運用 Runbook 等）。追加で記載したい項目があれば教えてください。