# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
ETL、データ品質チェック、ニュースベースのAIセンチメント、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件・依存関係
- セットアップ手順
- 環境変数 (.env) と設定
- 使い方（簡単な例）
  - ETL 実行
  - ニュースセンチメントスコア算出
  - 市場レジーム算出
  - 監査ログ DB 初期化
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は日本株のデータ基盤とリサーチ／自動売買に必要な共通機能を提供する Python パッケージです。  
主に以下の役割を担います:

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたローカルデータ保存・ETL パイプライン
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- RSS ニュース収集とニュース→銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄別センチメント）とマクロセンチメントの算出
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計上、バックテストや運用での Look-ahead バイアス回避に配慮し、日時取り扱いや DB クエリの境界を厳密にしています。

---

## 主な機能

- data/
  - jquants_client: J-Quants からの差分取得・保存（rate limiting、リトライ、トークン自動リフレッシュ）
  - pipeline: 日次 ETL（calendar / prices / financials）と品質チェックの統合
  - news_collector: RSS 取得、前処理、raw_news 保存、SSRF 保護
  - quality: データ品質チェック（欠損、重複、スパイク、将来日付）
  - audit: 監査テーブル定義と初期化ユーティリティ（DuckDB）
  - calendar_management: 営業日判定・next/prev_trading_day など
  - stats: zscore 正規化等のユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得→ai_scores 保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に書き込み
- research/
  - factor_research: mom/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- config.py: .env 自動ロード、Settings クラスで設定を集中管理

---

## 必要条件・依存関係

最小実行環境（一例）
- Python 3.10+
- pip installable パッケージ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外はこれらを想定）

実際の requirements はプロジェクトの packaging に合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成・アクティベート（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （パッケージ配布ファイルがある場合は pip install -e . など）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと、自動で読み込まれます（config.py が自動読み込み）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト時）。

5. DuckDB データベースや SQLite ファイルの配置先ディレクトリを作成（設定次第）
   - デフォルトは data/kabusys.duckdb 等を使用します。settings.duckdb_path の値を参照。

---

## 環境変数（主なもの）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KABUSYS_ENV=development
LOG_LEVEL=INFO

主要ポイント:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL に必要）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行に必要）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注がある場合）
- DUCKDB_PATH / SQLITE_PATH: データ・監視 DB のパス

Settings は kabusys.config.settings として利用できます。

---

## 使い方（コード例）

以下はライブラリ内部の関数を呼ぶ簡単な例です。プロジェクトに CLI がある場合はそれを使ってください。ここでは Python REPL / スクリプトからの呼び出し例を示します。

共通: DuckDB 接続を作成して渡す方法の例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（prices / financials / calendar と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 03, 20))
print(f"scored {count} codes")
```

3) 市場レジーム (bull/neutral/bear) を算出して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# テーブルが作成され、UTC タイムゾーン設定が適用される
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# リストとして各銘柄のファクター辞書が返る
```

注意:
- OpenAI を使う機能は OPENAI_API_KEY が必要です。api_key を関数引数で注入することも可能です（テスト容易性のため）。
- J-Quants API を叩く機能は JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。

---

## 運用上の注意点・設計方針（抜粋）

- Look-ahead バイアス対策: モジュールの多くは date.today() / datetime.today() を参照せず、呼び出し側から target_date を渡す設計になっています。バックテスト用途での利用はこの点に注意してください。
- ETL は差分更新とバックフィル機能を持ち、品質チェックは Fail-Fast ではなく問題を収集して報告します。
- ニュース収集は SSRF 対策、XML ハードニング（defusedxml）、トラッキングパラメータ除去などに配慮しています。
- J-Quants クライアントは rate limit（120 req/min）とリトライ・トークン自動更新を備えています。
- OpenAI 呼び出しはリトライ・エラー耐性を持ち、失敗時にはフェイルセーフ（スコア 0.0）を採用する箇所があります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py (score_news export)
  - news_nlp.py (ニュースセンチメント -> ai_scores)
  - regime_detector.py (市場レジーム判定 -> market_regime)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、保存関数)
  - pipeline.py (ETL パイプライン / run_daily_etl)
  - etl.py (ETLResult export)
  - news_collector.py (RSS 収集・正規化)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等)
  - calendar_management.py (営業日判定、calendar_update_job)
  - audit.py (監査ログスキーマ定義 / init)
- research/
  - __init__.py
  - factor_research.py (momentum/value/volatility)
  - feature_exploration.py (forward returns / IC / summary)

各モジュールには docstring と詳細な設計メモが付与されています。

---

## サポート・拡張

- 新しい RSS ソースを追加する場合は data/news_collector.py の DEFAULT_RSS_SOURCES を編集し、news_collector の保存ロジックを活用してください。
- ETL の取得先や保存スキーマを変更する場合は data/jquants_client と data/pipeline を拡張してください。
- OpenAI モデルやプロンプト設計は ai/news_nlp.py / ai/regime_detector.py に集約されています。

---

README はここまでです。具体的な実行コマンドやパッケージ化手順（setup.cfg / pyproject.toml によるインストール）を追加したい場合は、環境（CI/CD / デプロイ手順）情報を教えてください。必要に応じて README を追記します。