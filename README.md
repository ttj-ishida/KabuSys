KabuSys
=======

概要
----
KabuSys は日本株のデータパイプライン／リサーチ／自動売買（監視・監査）を想定したPythonパッケージです。  
主な目的は以下です。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたデータ保存・ETL（差分取得／バックフィル／品質チェック）
- ニュースの収集・NLP（LLM を使った銘柄センチメント評価）
- 市場レジーム判定（MA200 とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレースを保証する監査DB）
- 運用用の設定管理・監視フレームワーク（設定は環境変数 / .env）

機能一覧
--------
主要な機能（モジュール単位）:

- kabusys.config
  - .env/.env.local の自動読み込み（プロジェクトルート判定）と環境変数経由の設定管理
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（差分取得、ページネーション、再試行、レート制御）
  - pipeline / etl: 日次 ETL パイプライン（calendar / prices / financials）と ETL 結果クラス
  - calendar_management: JPX カレンダーの扱い・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS からのニュース収集（SSRF対策・トラッキング除去・前処理）
  - audit: 監査ログ (signal_events / order_requests / executions) のスキーマ初期化と監査DBユーティリティ
  - stats: Zスコア正規化など共通統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に投げ銘柄ごとの ai_score を生成・ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321)のMA200乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（| 演算子、型注釈の使用に依存）
- DuckDB を利用（duckdb パッケージ）
- OpenAI API を利用する機能には openai パッケージが必要
- RSS パースに defusedxml を使用

最低限の必要パッケージ例（pip）
- duckdb
- openai
- defusedxml

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. このパッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数
- このプロジェクトは環境変数から動作設定を読み込みます。主要な環境変数:

  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須): kabuステーション API パスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID (必須): Slack チャンネル ID
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 動作環境 (development / paper_trading / live)（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- .env 自動読み込み:
  - パッケージ読み込み時に、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local (override) > .env
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（主なユースケース）
-------------------------

1) DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントスコア付与（LLM を使用）
- 事前に OPENAI_API_KEY を環境変数で設定する必要があります。

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

4) 市場レジーム判定（MA200 とマクロニュースの合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

ret = score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算（研究用途）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
```

6) 監査ログスキーマ初期化 / 監査DB作成
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 監査専用 DB の初期化（ファイル or ":memory:"）
audit_conn = init_audit_db("data/audit.duckdb")
# 既存接続へスキーマ追加
# init_audit_schema(conn, transactional=True)
```

注意点・運用メモ
- LLM 呼び出し（OpenAI）はリトライ・タイムアウト等を実装していますが、API キー必須です。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装済みです。get_id_token() を使った自動リフレッシュ処理があります。
- ETL / 品質チェックは部分失敗を許容してログと ETLResult にエラー情報を残します（Fail-Fast を避ける設計）。
- テスト時に .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています。

ディレクトリ構成
----------------

主要ファイル・ディレクトリ（src/kabusys 以下）:

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
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - news_collector.py
  - (その他 ETL 補助モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py で各研究用ユーティリティをエクスポート

（注）リポジトリにはさらに strategy / execution / monitoring 等のパッケージが想定されていますが、このコードベースには上記のモジュール群が含まれています。

ライセンス / 貢献
----------------
この README はコードベースの概要ドキュメントです。ライセンスや貢献方法はリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

追加の情報が必要であれば、使用したいユースケース（例: バックテスト向けのデータ抽出、運用用 ETL スケジューリング、監査DB の統合等）を教えてください。具体的なコード例や運用手順を補足します。