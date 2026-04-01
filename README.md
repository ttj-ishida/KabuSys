KabuSys
=======

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買補助ライブラリです。
本リポジトリは主に以下の機能群を提供します。

- データ収集（J-Quants API を用いた株価/財務/カレンダーの差分 ETL、RSS ニュース収集）
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ニュース NLP（OpenAI を用いた銘柄ごとのニュースセンチメント算出）
- 市場レジーム判定（ETF の MA とマクロニュースを組み合わせた判定）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル・初期化ユーティリティ）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新・DuckDB 保存）

プロジェクト概要
----------------

KabuSys は DuckDB をデータストアとして利用し、J-Quants API や RSS、OpenAI と連携して
データの取得／正規化／品質チェック／特徴量算出／AIスコアリング／監査ログ作成までをサポートする
Python モジュール群です。バックテスト用データ整備や運用 ETL、研究用解析、AI を使ったニュース評価、
および取引監査ログの初期化といった用途を想定しています。

機能一覧
--------

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパ（必須設定の検査、型変換、env / log level チェック）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
  - pipeline: 日次 ETL（run_daily_etl 等）、差分 ETL ヘルパー
  - news_collector: RSS 取得・正規化・raw_news への保存ロジック（SSRF 対策・サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログテーブル生成・初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（gpt-4o-mini を利用）
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせた市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

1. Python 環境を用意（推奨: 3.10+）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 推奨パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   例:
     pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）
   - 開発時にインストールする場合:
     pip install -e .

4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID

その他（任意）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, ...（監視・運用用）

サンプル .env（例）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO
- KABUSYS_ENV=development

使い方（基本例）
---------------

以下はライブラリを直接インポートして使う例です。DuckDB 接続は duckdb.connect(...) で取得します。

1) DuckDB に接続して ETL を日次で実行（run_daily_etl の例）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（OpenAI を使って銘柄ごとのスコアを ai_scores テーブルへ書き込む）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロ記事を組み合わせて market_regime に書き込む）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化する（監査専用 DB）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/monitoring_audit.duckdb"))
# conn を使って order_requests / signal_events / executions 等を参照・操作できます
```

5) 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

注意点・運用上のヒント
- OpenAI 呼び出しは API レートや料金が発生します。テスト時はモック（unittest.mock.patch）を推奨します。
- news_nlp と regime_detector は OpenAI の JSON mode を期待したレスポンス構造でパースしています。レスポンスの妥当性チェック・フォールバックが組み込まれていますが、モデルや API の振る舞いによる差異に注意してください。
- .env の自動読み込みはパッケージ起動時に行われ、OS 環境変数を保護するため .env の上書きについては制御されています。テスト等で自動ロードを止める場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限や 401 トークン更新ロジックは jquants_client に実装されています。ID トークンは内部キャッシュされ、必要時に自動リフレッシュされます。

ディレクトリ構成（主要ファイル）
---------------------------

src/kabusys/
- __init__.py
- config.py                      （環境変数 / 設定管理）
- ai/
  - __init__.py
  - news_nlp.py                  （ニュース NLP / OpenAI インテグレーション）
  - regime_detector.py           （市場レジーム判定）
- data/
  - __init__.py
  - jquants_client.py            （J-Quants API クライアント + DuckDB 保存）
  - pipeline.py                  （ETL パイプライン / run_daily_etl 等）
  - etl.py                       （ETL 型の再公開）
  - news_collector.py            （RSS 収集）
  - quality.py                   （データ品質チェック）
  - calendar_management.py       （市場カレンダー管理）
  - stats.py                     （統計ユーティリティ）
  - audit.py                     （監査ログスキーマ/初期化）
- research/
  - __init__.py
  - factor_research.py           （ファクター計算）
  - feature_exploration.py       （IC/forward returns/summary 等）
- ai, research, data 以下にさらに詳細なヘルパーモジュールあり

ライセンス・貢献
----------------
（本 README にライセンス情報は含まれていません。リポジトリルートの LICENSE を参照してください）

フィードバック・バグ報告
-----------------------
問題や改善提案があれば Issue を作成してください。テストケースや再現手順があると対応が早くなります。

以上です。必要であれば README を README.md 形式で整形して .env.example のテンプレートを追加することもできます。どの程度の細かさでサンプルを載せたいか教えてください。