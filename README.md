# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援・監査・ETL・取引監視を含む自動売買プラットフォームのコアライブラリ群です。DuckDB を内部データベースとして利用し、J-Quants／kabuAPI／OpenAI 等と連携する設計になっています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（サンプル）
- 環境変数（.env の例）
- ディレクトリ構成（主要モジュール説明）

---

プロジェクト概要
- KabuSys は日本株のデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、データ品質チェック、監査ログ（約定トレーサビリティ）などを備えたバックエンドライブラリです。
- DuckDB を用いたローカル DB を中心に、ETL パイプラインや研究用ファクター計算、取引実行前後の監査ログ取り扱い、ニュースセンチメント評価等を行います。
- Look-ahead bias 回避、API リトライやレート制御、フェイルセーフ（API 失敗時のフォールバック）を設計方針に含めています。

---

主な機能
- データ取得・保存
  - J-Quants からの株価日足（OHLCV）・財務データ・JPX カレンダー取得と DuckDB への冪等保存
  - RSS ベースのニュース収集と記事の正規化・保存
- ETL / バッチ
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック の一連処理）
  - 差分更新・バックフィル機能
- 品質チェック
  - 欠損（OHLC）・スパイク検出・重複・日付不整合チェック（QualityIssue 構造で集約）
- AI（OpenAI）連携
  - ニュースを銘柄ごとに統合して LLM でセンチメント評価（ai_scores への書き込み）
  - マクロニュースと ETF(1321) の MA200 乖離から市場レジーム（bull/neutral/bear）を判定
  - OpenAI 呼び出しは JSON mode を利用、エラーハンドリング・リトライ実装あり
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、Zスコア正規化等
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを用いたトレーサビリティと初期化ユーティリティ
- その他
  - システム設定読み込み（.env / .env.local / 環境変数）
  - ニュースの SSRF 対策、受信サイズ制限、URL 正規化など堅牢な実装

---

セットアップ手順（開発環境例）
1. Python（3.10+ 推奨）を用意
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリ以外の依存がある場合は requirements.txt / pyproject.toml を参照してください
   - 例:
     pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に .env/.env.local を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. DuckDB データベース用ディレクトリを作成（必要に応じて）
   - デフォルトパスは data/kabusys.duckdb（設定で変更可能）
6. OpenAI / J-Quants の API キーなどを用意（下記参照）

---

環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jq API 認証に使用）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知のチャンネル ID
- KABU_API_PASSWORD: kabuステーション API にアクセスする場合のパスワード

OpenAI:
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime で使用）

システム / DB:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB、デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_ENV (development / paper_trading / live)

自動 .env ロード:
- プロジェクトルートにある .env と .env.local は自動で読み込まれます（.env.local が優先して上書き）。ただし OS 環境変数が優先され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

.sample .env（README 用例）
（実際のシークレットは決してコミットしないでください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

使い方（サンプル）
- DuckDB に接続して日次 ETL（run_daily_etl）を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリ作成は自動
```

注意点
- OpenAI 呼び出しには課金が発生するため、API キーとコストに注意してください。
- DuckDB への書き込みは ON CONFLICT による冪等性を意識した処理になっていますが、バックアップやロールバック方針は運用に合わせてください。
- datetime.today()/date.today() を不注意に用いるとルックアヘッドバイアスを招く設計上の注意があります。ライブラリ側はできる限り target_date を明示する方針です。

---

ディレクトリ構成（主なファイルと役割）
- src/kabusys/__init__.py
  - パッケージの基本設定（version, exported サブパッケージ）
- src/kabusys/config.py
  - .env / 環境変数の自動読込、Settings クラス（各種設定プロパティ）
- src/kabusys/ai/
  - news_nlp.py: ニュースの LLM センチメント化（銘柄別 ai_scores 生成）
  - regime_detector.py: ETF(1321) MA200 とマクロニュースから市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API 呼び出し、レート制御、保存ロジック（raw_prices, raw_financials, market_calendar 等）
  - pipeline.py: ETL の上位エントリ（run_daily_etl 等）および個別 ETL ジョブ
  - etl.py: ETLResult の再エクスポートインターフェース
  - news_collector.py: RSS 収集、前処理、raw_news への保存
  - calendar_management.py: JPX カレンダー管理と営業日判定ロジック（is_trading_day / next_trading_day 等）
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ（signal_events / order_requests / executions）DDL と初期化ロジック
- src/kabusys/research/
  - __init__.py: 研究用 API エクスポート
  - factor_research.py: Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数
- src/kabusys/ai/__init__.py
  - AI サブモジュールの公開 API（score_news 等）

---

開発上の補足
- テストや CI で自動的に .env を読み込みたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しの関数はテストでモックしやすいように設計されています（内部の _call_openai_api 等を patch 可能）。
- DuckDB の executemany へ空リストを渡すとエラーとなるバージョンがあるため、ライブラリ側で空チェックをしています。

---

貢献・ライセンス
- この README はコードベースからの抜粋に基づく概要ドキュメントです。実稼働に使う場合は必ず追加の運用手順（バックアップ、監視、キー管理、コスト管理）を設計してください。
- ライセンス情報はプロジェクトのルート（LICENSE / pyproject.toml 等）を参照してください。

---

不明点や追加で README に入れたい情報（例: CI 設定、実行スクリプト例、ユニットテストの実行方法など）があれば教えてください。README をそれに合わせて拡張します。