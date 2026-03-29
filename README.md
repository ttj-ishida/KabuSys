# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株向けのデータプラットフォーム・研究・自動売買基盤を想定した Python パッケージ群です。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- データ取得・ETL（J-Quants API 経由）と品質チェック
- ニュースの収集と LLM による記事センチメント評価（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- マーケットカレンダー管理（JPX）
- 監査ログ（signal → order_request → execution）の初期化ユーティリティ
- 環境設定の集中管理（.env 自動ロード）

主な機能一覧
---------------
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: 日次のデータ取得・保存・品質チェックを実行
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch / save の両方向を含む堅牢な取得・保存処理（レート制御、リトライ、トークン自動リフレッシュ）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存想定（SSRF対策・サイズ制限）
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合の検出
- 市場カレンダー（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ初期化（kabusys.data.audit）
  - 監査テーブル群（signal_events / order_requests / executions）とインデックスの作成、init_audit_db ユーティリティ
- AI コンポーネント（kabusys.ai）
  - news_nlp.score_news: ニュース記事を LLM で銘柄別スコア化して ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュースセンチメントを合成して market_regime を算出・保存
- 研究ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算、IC・統計要約、zscore_normalize

セットアップ手順
----------------

前提
- Python 3.10+（コード中の型ヒント（X | Y）や最新構文を想定）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（AI 機能を利用する場合）
- defusedxml（ニュース RSS パースの安全化）

推奨インストール（例）
```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# 必要パッケージ（プロジェクトに requirements.txt があればそちらを使用）
pip install duckdb openai defusedxml
```

環境変数 / .env
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から自動で .env / .env.local を読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（必須・推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API を呼び出す場合に必要（score_news / score_regime の api_key を省略する場合は環境変数から取得）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（省略時: data/monitoring.db）
- KABUSYS_ENV: 動作環境 (development, paper_trading, live)（省略時: development）
- LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（省略時: INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

使い方（主要ユースケース）
-------------------------

以下はライブラリを直接呼ぶ最小実例です。実際は CLI やジョブランナー（cron / Airflow / GitHub Actions 等）から呼び出して運用することを想定しています。

1) DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム判定（regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit）データベース初期化
```python
from kabusys.data.audit import init_audit_db

# ファイルを指定して新規 DB 作成（親ディレクトリを自動作成）
conn = init_audit_db("data/audit.duckdb")
# conn を使って後続処理を行う
```

5) 研究用ユーティリティ（ファクター計算例）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は list[dict] 形式
```

注意点（設計方針からの重要事項）
- ルックアヘッドバイアス防止:
  - 各モジュールは date.today() / datetime.today() を内部で参照しない設計（ターゲット日を引数で与える）。
  - prices_daily や raw_news へのクエリは target_date 未満 / 排他条件などで未来データを参照しない。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE により冪等に実行される（save_* 関数）。
  - ETL はバックフィル（過去数日を再取得）を行い API 後出しを吸収する。
- フェイルセーフ:
  - AI（OpenAI）呼び出し失敗時はゼロスコア等のフォールバックを行い処理を継続する（例: macro_sentiment = 0.0）。
- テスト容易性:
  - 一部内部 API 呼び出しは容易にモックできる設計（例: news_nlp._call_openai_api を差し替え可能）。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
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
  - audit.py (監査用)
  - etl.py (ETL interface 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (監視用モジュール等: 実装があれば配置)
- strategy/ (戦略ロジック: 実装があれば配置)
- execution/ (約定実行ロジック: 実装があれば配置)

開発向け備考
-------------
- ロギング: settings.log_level で制御されます。開発時は LOG_LEVEL=DEBUG が便利です。
- 自動 .env ロード: プロジェクトルート判定は __file__ を起点に行うため、import 時のカレントワーキングディレクトリに依存しません。テスト時に自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト: OpenAI / ネットワーク・外部 API を伴う箇所はモックして単体テストを実行してください。AI 呼び出し関数や RSS の _urlopen などは差し替え可能に設計されています。

ライセンス・貢献
----------------
本 README はコードベースに基づく説明ドキュメントです。実際のリポジトリの LICENSE ファイルを参照してください。貢献方法や PR のフローはプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

お問い合わせ
------------
問題報告・機能要望は Issue にお願いします。運用や導入に関する質問は README に連絡先（Slack / メール等）を追記してください（本ドキュメントではプレースホルダとして省略しています）。

以上。必要であれば CLI 実行例・より詳細な環境変数一覧・サンプル .env.example を追加で作成します。どの情報を優先して追記しましょうか？