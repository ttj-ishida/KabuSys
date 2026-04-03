KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants API からのデータ取得・ETL、ニュース収集と LLM によるニュースセンチメント解析、ファクター計算（リサーチ用）、市場レジーム判定、監査ログ（トレーサビリティ）などをモジュール化して提供します。

主な用途例:
- 日次 ETL（株価・財務・市場カレンダー）の自動化
- ニュースを集めて銘柄ごとに AI によるセンチメント算出 → ai_scores へ保存
- ETF（1321）などを用いた市場レジーム判定（MA + マクロニュースの合成）
- 研究用にファクター/将来リターン/IC 等の統計解析
- 発注・約定に至る監査ログの保持（DuckDB）

機能一覧
--------
- 環境設定管理（.env 自動読み込み、必須変数の取得） — kabusys.config
- データ取得 / ETL
  - J-Quants API クライアント（株価 / 財務 / カレンダー） — kabusys.data.jquants_client
  - 日次 ETL パイプライン（差分取得・保存・品質チェック） — kabusys.data.pipeline
  - 市場カレンダー管理（営業日判定など） — kabusys.data.calendar_management
  - ニュース収集（RSS → raw_news） — kabusys.data.news_collector
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合） — kabusys.data.quality
  - 汎用統計ユーティリティ（Zスコア正規化等） — kabusys.data.stats
- AI / NLP
  - ニュースセンチメントスコアリング（gpt-4o-mini を想定） — kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF MA200 とマクロニュースを合成） — kabusys.ai.regime_detector.score_regime
- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等） — kabusys.research.factor_research
  - 将来リターン計算、IC、統計サマリ等 — kabusys.research.feature_exploration
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義・初期化（DuckDB） — kabusys.data.audit

セットアップ手順
----------------

前提
- Python >= 3.10 を推奨（Union types (X | Y) を利用しているため）
- DuckDB, OpenAI SDK, defusedxml などの依存ライブラリが必要

1) リポジトリをクローンしてインストール（開発モード推奨）
   - pip を使用する例:
     - pip install -e .
     - 必要なパッケージが requirements.txt に含まれている場合: pip install -r requirements.txt

2) 主要な依存パッケージ（手動例）
   - pip install duckdb openai defusedxml

3) 環境変数 / .env を用意する
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（/ 推奨）環境変数（settings 参照）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必要な場合）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 実行時に利用）
- DUCKDB_PATH (任意) : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意) : 監視用 sqlite のパス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL : "DEBUG" / "INFO" / ...（デフォルト INFO）

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

使い方（コード例）
-----------------

基本的なパターンは DuckDB 接続を作成し、各 API を呼ぶ形です。以下は代表的な例を示します。

1) DuckDB 接続の作成
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL（株価／財務／カレンダーの差分 ETL）
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースのスコアリング（OpenAI を使う）
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか OPENAI_API_KEY 環境変数を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 監査ログ DB の初期化（監査用の専用 DuckDB）
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions とインデックスが作成されます

6) ニュース RSS の取得（単体）
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])

注意点 / 運用上のヒント
- OpenAI の呼び出しはコストが発生します。テストではモック化（unittest.mock.patch）して呼び出しを差し替えることを推奨します。
- score_news / score_regime は Look-ahead バイアスを避ける設計（target_date パラメータを明示）です。バックテスト時は必ず過去日を渡してください。
- J-Quants API はレート制限（120 req/min）や認証トークンのローテーションロジックが組み込まれています。get_id_token / _request 内の挙動を理解しておくとトラブルシュートが楽になります。
- データ保存は DuckDB に対して冪等（ON CONFLICT ... DO UPDATE）で行われます。ETL は部分失敗を考慮した実装です。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

src/kabusys/
- __init__.py
- config.py                                # 環境変数・設定の管理
- ai/
  - __init__.py
  - news_nlp.py                             # ニュースセンチメント解析（score_news）
  - regime_detector.py                      # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                       # J-Quants API クライアント（fetch/save）
  - pipeline.py                             # ETL パイプライン（run_daily_etl 等）
  - etl.py                                  # ETL 結果クラスの公開
  - calendar_management.py                  # 市場カレンダー管理
  - news_collector.py                        # RSS 取得・前処理
  - quality.py                               # データ品質チェック
  - audit.py                                 # 監査ログスキーマ初期化
  - stats.py                                 # 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py                       # ファクター計算（momentum/value/volatility）
  - feature_exploration.py                   # forward returns / IC / summary

主要なクラス・関数（抜粋）
- settings = kabusys.config.Settings()       # 各種設定をプロパティで提供
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.audit.init_audit_db(...)

ライセンス / 貢献
-----------------
本 README では省略します。実際のリポジトリに LICENSE ファイルがある場合はそちらを参照してください。バグ報告・改良提案は Issue / Pull Request で受け付けてください。

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。実際の運用では各モジュールの docstring（関数説明）やログ出力を参照し、API キーや DB のバックアップ・アクセス制御に十分注意してください。作業前にテスト環境で動作確認することを強く推奨します。