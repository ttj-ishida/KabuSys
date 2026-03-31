README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API などから市場データを収集・整備し、ニュース NLP / LLM によるセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（トレーサビリティ）など、アルゴリズム取引のバックエンド処理を支えるユーティリティ群を提供します。

主な用途例:
- 日次 ETL（株価・財務・市場カレンダー）の差分取得・保存・品質チェック
- RSS ニュースの収集と記事単位・銘柄単位の NLP スコアリング（OpenAI 使用）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用の DuckDB スキーマ初期化

機能一覧
--------
- 環境変数・設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須／任意設定のプロパティを提供
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API からの差分取得（ページネーション・レート制御・リトライ）
  - DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL 実行エントリポイント run_daily_etl
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後営業日取得 / カレンダー差分更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、安全対策（SSRF 対策・gzip 上限・XML 安全パース）と raw_news への保存準備
- AI（kabusys.ai）
  - ニュース NLP（score_news）: gpt-4o-mini を用いた銘柄別センチメント評価
  - 市場レジーム判定（score_regime）: ETF の MA とマクロニュース LLM を合成
  - どちらも JSON Mode を用いた厳格なレスポンス処理、リトライ・フォールバック実装
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリー
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義と初期化機能（init_audit_db / init_audit_schema）

前提 / 要件
-----------
- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

インストール（開発環境向け）
---------------------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）
3. パッケージをローカルインストール（任意）
   - pip install -e .

設定（環境変数 / .env）
---------------------
ルートプロジェクトに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

重要な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須): Slack 通知用トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY (AI モジュール利用時に必要)

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

セットアップ手順（実践）
---------------------
1. 環境変数を準備（上記 .env を作成）
2. DuckDB ファイルの親ディレクトリを作成:
   - mkdir -p data
3. 監査ログ用 DB を初期化（オプション）:
   - from kabusys.data.audit import init_audit_db
   - conn = init_audit_db("data/audit.duckdb")  # :memory: も可
4. ETL 等で利用する DuckDB 接続:
   - import duckdb
   - from kabusys.config import settings
   - conn = duckdb.connect(str(settings.duckdb_path))

使い方（クイックスタート）
------------------------

1) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 30))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 30))
print("written:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 30))
```

4) 監査ログスキーマの初期化（audit 用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。signal_events / order_requests / executions テーブルが作成される。
```

注意点 / 実運用上の留意事項
------------------------
- OpenAI 呼び出しは API レートやコストが発生します。API キーやレート制御・バッチサイズ設定に注意してください。
- J-Quants API はレート制限（120 req/min）や認証フローがあるため、本ライブラリではレートリミット、リトライ、トークン自動リフレッシュを実装していますが、運用では適切な id_token のキャッシュ・監視を行ってください。
- ETL の保存先テーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores など）は本リポジトリに明示的なスキーマ初期化スクリプトが含まれていない箇所があります（audit のみ初期化機能あり）。実運用ではスキーマ定義ファイルを別途適用してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップできます。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            -- ETL パイプライン・run_daily_etl 等
    - etl.py                 -- ETLResult 再エクスポート
    - calendar_management.py -- 市場カレンダー判定・更新ジョブ
    - news_collector.py      -- RSS 収集・前処理
    - quality.py             -- データ品質チェック（QualityIssue）
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - audit.py               -- 監査ログ（schema 定義・init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     -- Momentum/Value/Volatility 等
    - feature_exploration.py -- forward returns / IC / rank / summary
  - monitoring/               -- （将来の監視モジュール等を想定）
  - execution/                -- （発注処理等、別モジュール想定）
  - strategy/                 -- （戦略本体はここに追加）
  - data/                     -- （データ関連ユーティリティ）

開発・テストのヒント
--------------------
- OpenAI / J-Quants の外部 API 呼び出しはユニットテストでモック置換することを推奨します（本コード内でもテスト容易性を考え、_call_openai_api 等を差し替え可能にしてあります）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml の親）を探索します。テスト環境で isolation が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

最後に
------
この README はコードベースの主要機能と使い方の概要を示したものです。実際の運用・本番化にあたっては、セキュリティ（API キー管理）、監視、ロギング、例外ハンドリング、テーブルスキーマ管理などを十分に設計・検証してください。必要であれば初期スキーマ SQL や運用手順のドキュメント化を追加できます。