# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株向けの自動売買プラットフォーム／データパイプラインの基盤ライブラリです。本コードベースは以下の主要機能群を含みます。
- データ収集（J-Quants API 経由の株価・財務・マーケットカレンダー、RSS ニュース収集）
- ETL（差分取得、保存、品質チェック）
- ニュース NLP（OpenAI を用いた銘柄センチメントスコアリング）
- 市場レジーム判定（ETF + マクロニュースを組み合わせた判定）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 環境設定管理（.env 自動ロード／保護）

設計上のポイント
- Look-ahead バイアスを避ける設計（内部で date.today()/datetime.today() を参照しない関数や、DB クエリにおける排他条件など）
- DuckDB を中心としたローカル分析・永続化
- OpenAI（gpt-4o-mini）を使う NLP パイプライン（JSON Mode を想定）
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを実装

主な機能一覧
---
- data/
  - jquants_client: J-Quants API クライアント（fetch/save、ページネーション、rate-limit、リトライ）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management: JPX カレンダー管理と営業日ロジック
  - audit: 監査ログスキーマ初期化・DB作成ユーティリティ
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- ai/
  - news_nlp: ニュースを銘柄ごとに LLM へ送りセンチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジームを判定
- research/
  - factor_research: Momentum/Value/Volatility 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー等
- config.py: 環境変数 / .env 自動読み込みロジックと Settings オブジェクト
- audit/schema 初期化、DuckDB 用ユーティリティ等

セットアップ手順
---
1. Python 環境を用意
   - 推奨: Python 3.10+（typing 機能を多用）
2. 必要パッケージをインストール
   - 主に以下を使います（プロジェクト依存の正確な requirements は別途管理してください）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発時は追加で pytest などを入れてください
3. ソースをインストール（開発モード）
   - git clone <repo>
   - cd <repo>
   - pip install -e .
4. 環境変数（.env）を準備
   - プロジェクトルートの .env または .env.local を自動的に読み込みます（OS 環境変数の優先）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（主なもの）
---
以下はコード内で _require() により必須扱いとなる変数例です。プロジェクトルートに .env ファイルを用意してください。

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token() で ID トークンを得るために使用します。
- KABU_API_PASSWORD
  - kabu ステーション API を使う場合のパスワード（本コードベースの一部モジュールで参照）。
- SLACK_BOT_TOKEN
  - Slack に通知を出す場合の Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — モニタリング DB のパス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI キー（score_news / score_regime で省略可：関数引数で渡すことも可能）

サンプル .env（例）
---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（クイックスタート）
---
以下は Python REPL やスクリプトから呼び出す簡単な例です。DuckDB の接続は duckdb.connect() を利用します。

1) 日次 ETL を実行する（prices / financials / calendar の差分取得・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースによる銘柄スコアリング（OpenAI API 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="your-openai-key")
print(f"scored: {count}")
```

3) 市場レジーム判定（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="your-openai-key")
```

4) 監査ログ用の DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

API の注意点
- OpenAI 呼び出しは JSON Mode（厳密な JSON を期待）での入力/出力を前提としています。レスポンスパースに失敗した場合はフォールバック（スコア 0.0 など）する実装です。
- J-Quants API はレート制限（120 req/min）およびリトライロジックが組み込まれています。refresh token → id token の自動更新にも対応。
- ETL / ニューススコアリング / レジーム判定関数は Look-ahead バイアスを避ける工夫（対象日未満のデータのみ参照等）を施しています。バックテスト等で使用する際は注意してください。

ディレクトリ構成（主要ファイル）
---
ツリー（抜粋）
- src/kabusys/
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
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (監視系は __all__ に含まれるが、実装はプロジェクトによる)
  - execution/ (発注ロジック用プレースホルダ)
  - strategy/ (戦略実装用プレースホルダ)

各モジュールの責務（簡潔）
- config.py: .env 自動ロード、Settings オブジェクト（環境変数の型・検証）
- data/jquants_client.py: API 呼び出し・保存処理（raw_prices, raw_financials, market_calendar など）
- data/pipeline.py: 日次 ETL のオーケストレーションと ETLResult
- data/news_collector.py: RSS 収集と前処理・冪等保存
- data/quality.py: 品質チェックロジック（QualityIssue を返す）
- ai/news_nlp.py: LLM を使った銘柄ごとのニュースセンチメント算出（ai_scores テーブルへ書き込み）
- ai/regime_detector.py: ETF + マクロニュースを合成して market_regime に書き込み
- research/*: ファクター／統計解析ユーティリティ

運用上の注意
---
- 本システムは実取引に用いる前に厳密なテストと監査を実施してください。特に発注・約定周り（kabu ステーションやブローカー API）を組み合わせる場合の安全対策は重要です。
- OpenAI や J-Quants の API キーは適切に管理し、公開リポジトリに含めないでください。
- .env 自動読み込みはプロジェクトルート（.git や pyproject.toml があるディレクトリ）を基準に行われます。テスト時に自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュース収集や LLM 呼び出しはコストが発生します。バッチサイズやリトライ設定は適宜調整してください。

貢献
---
バグ報告・機能提案は issue を立ててください。設計思想（Look-ahead バイアス回避、冪等性、フェイルセーフ）に沿った実装を心がけてください。

ライセンス
---
このリポジトリにライセンスファイルが無い場合は、利用前にライセンス方針を確認してください。

補足 / 参考
---
- 設定値は kabusys.config.settings オブジェクトから簡単に取得できます（例: from kabusys.config import settings; settings.duckdb_path）。
- DuckDB を直接操作してスキーマを確認・作成してください（data.audit.init_audit_schema などのユーティリティあり）。
- テスト時は OpenAI / ネットワーク呼び出しをモックする設計になっています（モジュール内の _call_openai_api 等を patch）。

以上が README の要約です。必要に応じて README を拡張（例: 実際の SQL スキーマ、CI/CD、デプロイ手順、より詳細な API 使用例）できます。追加したい項目があれば教えてください。