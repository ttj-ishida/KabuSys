KabuSys — 日本株自動売買システム
=============================

概要
---
KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。  
主に以下を目的としています。

- J-Quants API からのデータ取得（株価、財務、JPX カレンダー）
- ニュース収集・NLP による銘柄センチメント算出（OpenAI 利用）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ETL／データ品質チェック、マーケットカレンダー管理
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

本 README ではプロジェクトの主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

主な機能
---
- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション・トークン自動リフレッシュ・レート制御を実装
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックを実行して QualityIssue を収集
- ニュース収集 & NLP
  - RSS からニュースを収集し raw_news に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント scoring（ai_scores へ書込）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）判定
- 研究（research）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ランク化・統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数から設定を読み込み、settings オブジェクトでアクセス可能

セットアップ手順
---
前提
- Python 3.10+（typing の union 型注釈等を想定）
- ネットワーク接続（J-Quants、OpenAI、RSS 等）

1. リポジトリをクローン・プロジェクトルートへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必要となる主な外部依存：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。）

4. 環境変数の設定
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）を起点に、自動で .env/.env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 読み込みの優先順位（強い順）:
     1. OS 環境変数
     2. .env.local（存在すれば .env の値を上書き。ただし OS 環境変数は保護）
     3. .env（OS 未設定項目のみ）
   - 最低限設定が必要な環境変数（コード参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
   - その他（任意またはデフォルトあり）:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   - .env のサンプル例（プロジェクトに .env.example があればそれを参考にしてください）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. データベース初期化（監査ログ用の例）
   - Python コンソールやスクリプトで:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # 親フォルダがなければ自動作成
     ```
   - ETL 等で使う DuckDB 接続は settings.duckdb_path を使って接続するのが簡単です。

基本的な使い方
---
以下は主要ユーティリティの使用例（Python スクリプト / REPL から）。

設定値にアクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

ニュースセンチメントの算出（OpenAI 必要）
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# api_key=None の場合は環境変数 OPENAI_API_KEY を参照
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

市場レジーム判定（OpenAI 必要）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログスキーマ初期化（既存接続を使う）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

研究用ファクター計算（例）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
```

注意点・運用上のポイント
---
- Look-ahead bias（未来情報参照）の防止:
  - 多くのモジュールは内部で date.today() を直接参照せず、明示的な target_date を受け取る設計になっています。バックテストや再現性のために target_date を明示してください。
- 環境変数の扱い:
  - OS 環境変数が最優先で保護され、.env.local は .env を上書きします。機密情報（API トークン等）は決してリポジトリにコミットしないでください。
  - テストや CI で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API:
  - OpenAI 呼び出しはリトライやフォールバック（失敗時 0.0）を実装していますが、API 利用量・コストには注意してください。
  - J-Quants の API レート制限を遵守するためにレートリミッタやリトライを組み込んでいます。
- RSS フィードの取得では SSRF・XML Bomb 等の脅威に対する対策を実装しています（スキーム検査、プライベート IP ブロック、defusedxml、レスポンスサイズ制限など）。

ディレクトリ構成（主要ファイル）
---
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ宣言・version
  - config.py — 環境変数 / 設定の読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py — 日次 ETL パイプライン（prices/financials/calendar）
    - stats.py — zscore 正規化等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
    - audit.py — 監査ログ（signal/order/execution）DDL と初期化
    - jquants_client.py — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py — RSS 取得・前処理・raw_news への保存用ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー等
  - ai, data, research 以下に多くの細かな実装が含まれます（上記は主要ファイルの抜粋）。

貢献・開発
---
- テスト:
  - OpenAI 呼び出し等は内部の _call_openai_api をモックしやすく設計されています（unittest.mock.patch を参照）。
- コーディング規約:
  - Look-ahead バイアスを避けるため、関数は可能な限り target_date を引数に取り、datetime.now()/date.today() の直接参照を避けています。
- 新しい機能の追加やバグ修正は PR を受け付けます。API トークンや機密情報は含めないでください。

ライセンス
---
（ここにプロジェクトのライセンス情報を記載してください — 元のリポジトリのライセンスに従ってください。）

最後に
---
この README はコードベースに基づく概要と使い方のガイドです。詳細は各モジュールの docstring を参照してください。必要であれば、具体的な操作（ETL スケジューリング、Slack 通知設定、kabuステーション連携など）についての追補ドキュメントを作成します。必要な項目があれば教えてください。