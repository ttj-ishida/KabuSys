KabuSys — 日本株自動売買 / 研究用ライブラリ
========================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、ETL、ニュースの NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）や市場レジーム判定などを含む自動売買・リサーチ基盤の Python モジュール群です。DuckDB を主要なオンディスク DB として利用し、OpenAI を用いたニュースセンチメント評価や J-Quants API 経由のデータ取得を想定しています。

主な機能
-------
- データ取得 / ETL
  - J-Quants API からの株価（日足）、財務情報、JPX マーケットカレンダー取得（差分更新・ページネーション対応・レート制御・リトライ付き）
  - ETL の一括実行（run_daily_etl）と個別ジョブ（prices / financials / calendar）
- データ品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集・前処理
  - RSS フィード取得、URL 正規化、SSRF 対策、前処理
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメントを ai_scores に保存（news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離から日次の市場レジームを判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等ファクター計算（research パッケージ）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブル定義と初期化ユーティリティ（DuckDB）
- 設定管理
  - .env（自動ロード可）および環境変数からの設定読み込み（kabusys.config.settings）

動作環境
-------
- Python 3.10+
- 依存（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多い）
※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

セットアップ手順
----------------
1. リポジトリをクローン / パッケージをインストール
   - 開発環境での編集・実行例:
     - git clone ... 
     - python -m venv .venv && source .venv/bin/activate
     - pip install -e .  （プロジェクトの packaging による）
   - あるいは必要なライブラリのみインストール:
     - pip install duckdb openai defusedxml

2. 環境変数 / .env の準備
   - KabuSys は起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
     - OPENAI_API_KEY — OpenAI を使う場合（score_news / score_regime が参照）
     - KABU_API_PASSWORD — kabuステーション API パスワード（settings.kabu_api_password）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合
   - 任意:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB; デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）

   例 .env（プロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB ファイル作成（初期化）
   - ETL 実行前に必要なスキーマを準備する場合、プロジェクトに初期化用スクリプトがある想定です。監査ログ専用 DB は kabusys.data.audit.init_audit_db を使って初期化できます（下記「使い方」参照）。

使い方（簡易サンプル）
--------------------

1) DuckDB に接続して ETL を走らせる（例: 日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env 等で設定可（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 27))
print(result.to_dict())
```

2) ニュース NLP（銘柄別センチメント）を実行
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 27), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 27), api_key=None)  # OPENAI_API_KEY を環境変数でも可
```

4) 監査ログ用 DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_duckdb.db")  # 親ディレクトリは自動作成されます
# conn_audit に対してアプリが order_requests / executions 等を記録できます
```

5) 研究用ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, target_date=date(2026, 3, 27))
# 結果は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

設定・実行に関する注意点
-----------------------
- Look-ahead バイアス対策
  - AI / ETL / リサーチモジュールは内部で date パラメータを明示的に受け取り、date.today()/datetime.today() を直接参照しない設計です。バックテスト用途では特に target_date を厳密に指定してください。
- API リトライ / フェイルセーフ
  - OpenAI / J-Quants 呼び出しはリトライやフォールバック（失敗時は 0.0 スコア等）を行う設計です。大規模失敗時はログを確認してください。
- 自動 .env 読み込み
  - プロジェクトルート検出により .env/.env.local が自動ロードされます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル / モジュール）
--------------------------------------------
- src/kabusys/
  - __init__.py         - パッケージ初期化、バージョン
  - config.py           - .env / 環境変数読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py       - ニュースセンチメントスコアリング（score_news）
    - regime_detector.py- マクロ + ETF MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py       - ETL パイプライン（run_daily_etl 等）、ETLResult
    - jquants_client.py - J-Quants API クライアント（取得・保存関数）
    - quality.py        - 品質チェック（check_missing_data 等）
    - calendar_management.py - マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py - RSS 取得・保存ユーティリティ
    - stats.py          - 共通統計ユーティリティ（zscore_normalize）
    - audit.py          - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - etl.py            - ETL インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py - Momentum/Value/Volatility 計算
    - feature_exploration.py - 将来リターン / IC / 統計サマリー
  - ai/ 及び research の詳細モジュール群

ログと監視
--------
- settings.log_level でログレベルを制御できます。運用時は適切なログ保持・ローテーション・外部監視を構築してください。
- Slack 連携用のトークン設定があり、将来的に通知機能を組み込めます（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。

開発・テスト
------------
- モジュールは外部 API 呼び出しを伴う箇所が多いため、ユニットテストでは API 呼び出し部分をモックすることが前提です（既に _call_openai_api の差し替えを想定した設計等）。
- settings の自動 .env ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。

補足
----
- ここに示した使い方は代表的な例です。実運用では認証トークンの安全管理、レート制限の考慮、エラーハンドリング、監査ログや監視の整備を必ず行ってください。
- パッケージ化 / 実行スクリプト / CI 設定等はリポジトリの他ファイル（pyproject.toml / scripts 等）を参照してください。

問い合わせ
---------
実装の意図や内部仕様（例: Look-ahead 防止の設計、ETL の振る舞い等）について不明点があれば、該当モジュール名と関数名を指定して質問してください。