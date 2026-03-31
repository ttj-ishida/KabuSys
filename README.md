# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データの ETL、ニュースセンチメント（LLM）によるスコアリング、ファクター計算、監査ログ／発注トレースなど、取引システムの基盤機能を提供します。

概要
- パッケージ名: `kabusys`
- 目的: J-Quants 等から株価・財務・カレンダー・ニュースを取得して DuckDB に保存し、機械学習/ルールベース戦略で利用できるデータ基盤と研究・実行支援機能を提供する。
- 設計方針（要点）
  - ルックアヘッドバイアスを避ける設計（日付処理で現在時刻に依存しない等）
  - DuckDB をメインの永続化層として使用（局所ファイル/インメモリ両対応）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価を実装（JSON Mode を使用）
  - API 呼び出しはリトライ／バックオフ、レート制御、トークン自動リフレッシュ等を実装
  - ETL / 品質チェック（quality） / 監査ログ（audit）等は冪等性を重視

主な機能一覧
- 環境設定
  - 自動 .env 読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 主要な環境変数を Settings オブジェクト経由で取得（必須チェックあり）
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（`jquants_client`）
    - 株価日足（daily_quotes）、財務データ、上場銘柄情報、JPX カレンダー取得
    - レート制限管理、リトライ、トークン自動刷新、ページネーション対応
  - ETL パイプライン（`pipeline.run_daily_etl`）
    - 市場カレンダー、株価、財務データの差分取得・保存・品質チェック
  - ニュース収集（RSS）と前処理（`news_collector`）
  - カレンダー管理（営業日判定、next/prev_trading_day など）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル）初期化ユーティリティ
- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー、Z スコア正規化
- AI（kabusys.ai）
  - ニュース NLP スコアリング（`score_news`）
  - 市場レジーム検出（ETF 1321 の MA200 とマクロニュースを合成して判定）`score_regime`
  - OpenAI 呼び出しはリトライ・フォールバック実装（異常時はフェイルセーフ）
- 監視・実行支援（execution / monitoring）
  - 監査テーブルや発注ログの整備により、シグナル→発注→約定までのトレースを保持

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python のバージョン
   - Python 3.10+ を推奨（型記法に | を使用しているため）
3. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 依存パッケージのインストール
   - もし requirements.txt があれば:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ例:
     - pip install duckdb openai defusedxml
   - 開発インストール（パッケージ化されている場合）
     - pip install -e .
5. 環境変数 / .env ファイル
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 読み込み順: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（README 用サンプル）
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略時デフォルト)
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=CXXXXXXX
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development | paper_trading | live
     - LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL
6. その他
   - OpenAI API を使用する機能を動かすには `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時に api_key を渡してください。

使い方（簡単な例）
- DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（AI スコア）を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等の操作が可能
```

- 市場カレンダー更新ジョブ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved", saved)
```

設定（Settings）について
- 設定は `kabusys.config.settings` オブジェクト経由で取得します。必須キーは取得時に ValueError を投げます。
  - 例:
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.slack_bot_token
    - settings.slack_channel_id
    - settings.duckdb_path  (Path オブジェクト)
    - settings.env  (development / paper_trading / live)
    - settings.log_level

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / .env ローダー / Settings
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py                 -- ニュース NLP スコアリング（LLM 呼び出し）
    - regime_detector.py          -- 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント / 保存関数
    - pipeline.py                 -- ETL パイプライン（run_daily_etl など）
    - etl.py                      -- ETLResult の再エクスポート
    - news_collector.py           -- RSS ニュース収集・前処理
    - calendar_management.py      -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                  -- データ品質チェック
    - stats.py                    -- zscore_normalize 等の統計ユーティリティ
    - audit.py                    -- 監査テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py          -- ファクター計算（momentum/volatility/value）
    - feature_exploration.py      -- forward returns / IC / summary / rank
  - research/* other modules...
  - (execution, monitoring, strategy 等のサブパッケージが存在する想定)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートに存在する場合）

注意事項 / 運用上のヒント
- OpenAI の呼び出しは料金およびレート制限が発生します。テスト時はモック化することを推奨します（コード内で _call_openai_api の差し替えを想定）。
- .env ファイルの自動読み込みはプロジェクトルート検出（.git / pyproject.toml）に依存します。CI やテスト時に不要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとバージョン依存で問題になるケースがあるため、コードは空チェックを行っています。カスタム操作を行う場合は注意してください。
- ETL や品質チェックは一部 API 失敗時にフェイルセーフ（処理スキップ）する設計です。呼び出し元でエラーリストを確認して適切に対応してください。

貢献・拡張
- ニュースソースの追加、AI モデルの変更、戦略ロジックや実行ブロック（ブローカー接続）の実装はモジュールを拡張することで対応できます。
- PR ではテスト（ユニット / 結合）と、外部 API 呼び出しをモック化したテストケースを含めることを推奨します。

---

この README はソースコード（主要モジュール）に基づいて作成しました。必要があれば、導入手順の詳細化（Docker / CI セットアップ例）、サンプル .env.example、実行用 CLI スクリプト例などを追加します。どの情報を優先して充実させるか教えてください。