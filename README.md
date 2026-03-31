README
======

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買処理群を提供する Python パッケージです。J-Quants API からのデータ取り込み（ETL）、ニュースの収集と LLM による NLP スコアリング、ファクター計算（研究用）、監査ログ／発注追跡用スキーマ、マーケットカレンダー管理などを含みます。

主な設計方針
- ルックアヘッドバイアス（未来情報参照）を避けるため、内部関数は明示的な target_date を受け取るか DB 上の過去データのみ参照します。
- DuckDB を用いたローカル DB 保存は冪等（ON CONFLICT）で行います。
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ・レート制御を組み込んで安全に実装されています。
- テスト容易性を考慮して API 呼び出し箇所は差し替え可能です（モック可能）。

機能一覧
--------
- data (ETL / quality / calendar / jquants client / news collector / audit)
  - 日次 ETL パイプライン（株価、財務、カレンダー）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - JPX マーケットカレンダー管理（営業日判定 / next/prev 等）
  - J-Quants API クライアント（レート制御、トークン更新、ページネーション）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - 監査ログ（signal_events, order_requests, executions）スキーマ初期化
- ai
  - ニュース NLP（銘柄毎のセンチメントを OpenAI で評価、ai_scores へ書き込み）
  - 市場レジーム判定（ETF 1321 の MA + マクロニュース LLM スコアで日次判定）
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- util / config
  - 環境変数/設定読み込み（.env 自動ロード、必要な設定値取得 API）

セットアップ手順
----------------

前提
- Python 3.10 以上（コードは X | Y 型アノテーション等を使用）
- システムに pip がインストールされていること

推奨インストール手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要ライブラリ（最低限）:
     pip install duckdb openai defusedxml
   - 実際のプロジェクトでは requirements.txt を用意している想定です:
     pip install -r requirements.txt

3. パッケージをインストール（編集可能モード）
   - プロジェクトルートで:
     pip install -e .

環境変数 / .env
- プロジェクトは起動時にプロジェクトルートの .env / .env.local（優先）を自動で読み込みます。
- 自動ロードを無効にするには環境変数を設定:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注系）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

.env.example（簡易）
- .env に以下を置く（実際の値は秘密扱い）
  JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（コード例）
-----------------

1) 基本設定の取得
from kabusys.config import settings
print(settings.duckdb_path, settings.env)

2) DuckDB 接続
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

3) 日次 ETL を実行する
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())

4) ニュース NLP スコアリングを実行（ai -> ai_scores に保存）
from kabusys.ai.news_nlp import score_news
from datetime import date
# OPENAI_API_KEY が環境変数に設定されているか、api_key を渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"wrote {n_written} ai_scores")

5) 市場レジーム判定を実行
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026,3,20), api_key=None)

6) 監査 DB を初期化（監査ログ用の独立 DB）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

注意点（利用時のポイント）
- OpenAI 呼び出しは API リトライ・フォールバック実装がありますが、API キーを設定するか関数に api_key を渡してください。
- AI スコアリング系は LLM レスポンスの形式を厳密な JSON として期待しますが、万一パースできない場合はフォールバック（スコア 0.0）やスキップします。
- ETL は冪等設計です（既存データは上書き）。ただし DuckDB の executemany に空リストを渡すとエラーになる箇所に対するガードが入っています。
- テストで .env の自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 # 環境変数・設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py             # ニュースの LLM スコアリング（ai_scores 書き込み）
  - regime_detector.py      # 市場レジーム判定（ETF MA + マクロ LLM）
- data/
  - __init__.py
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - etl.py                  # ETLResult 再公開
  - jquants_client.py       # J-Quants API クライアント + 保存関数
  - quality.py              # データ品質チェック
  - calendar_management.py  # マーケットカレンダー管理 / 営業日判定
  - news_collector.py       # RSS 収集（SSRF 対策・正規化）
  - audit.py                # 監査スキーマ定義・初期化
  - stats.py                # 共通統計ユーティリティ（z-score）
- research/
  - __init__.py
  - factor_research.py      # ファクター計算（momentum/value/volatility）
  - feature_exploration.py  # forward returns, IC, summary, rank
- research/... (他の関連モジュール)
- その他: strategy, execution, monitoring パッケージが __all__ に含まれます（実装済みファイル群による）

トラブルシューティング
---------------------
- .env が読み込まれない／テストで困る:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効にできます。
- OpenAI 呼び出しをテストで差し替えたい:
  モジュール内の _call_openai_api を unittest.mock.patch で差し替える設計になっています（news_nlp, regime_detector に実装あり）。
- J-Quants API エラー:
  jquants_client はトークン自動リフレッシュ・再試行・レート制御を組み込んでいます。認証エラーは JQUANTS_REFRESH_TOKEN の確認をしてください。

ライセンス / 貢献
-----------------
（ここではライセンスファイルや貢献ルールは含まれていません。プロジェクトに合わせて LICENSE / CONTRIBUTING を追加してください。）

以上。必要であれば、README にサンプル .env.example ファイルや CLI（もしあれば）説明、より詳細な API 使用例を追加します。どの部分を優先して追記しますか？