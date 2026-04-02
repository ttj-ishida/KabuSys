# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL によるデータ取得、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日時を直接参照しない設計）
- DuckDB を中心としたローカル DB（ファイル）でデータを保持
- 外部 API 呼び出しは再試行・レート制御・フォールバックを備えた堅牢な実装
- 冪等性を重視（ON CONFLICT / DELETE→INSERT 等）

---

## 主要機能（概要）
- データ取得 / ETL
  - J-Quants API から株価日足、財務情報、JPX カレンダーを差分取得・保存（kabusys.data.pipeline）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去）と raw_news への保存（kabusys.data.news_collector）
  - OpenAI を用いたニュースセンチメント集約（銘柄別 ai_scores に書込み）— score_news（kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して日次の market_regime を判定（kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- カレンダー管理
  - market_calendar の取得・営業日判定・next/prev_trading_day 等（kabusys.data.calendar_management）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ（kabusys.data.audit）
- 設定管理
  - .env または OS 環境変数からロード、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（kabusys.config）

---

## 必要環境 / 依存
- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続が必要（J-Quants / OpenAI / RSS 等）

（プロジェクトに requirements.txt / pyproject.toml があればそちらでインストールしてください）

例（ミニマム）:
pip install duckdb openai defusedxml

---

## セットアップ手順（開発用）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   pip install -e .               # パッケージ化されている場合
   または
   pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートの .env / .env.local を利用可能（自動ロード）
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

必須となる主な環境変数（README 用サンプル）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に使う）
- KABU_API_PASSWORD: kabuステーション API のパスワード（実行モジュールが使う）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime など）
オプション:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=......
OPENAI_API_KEY=......
SLACK_BOT_TOKEN=......
SLACK_CHANNEL_ID=......
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

- DuckDB 接続を作成して ETL を実行（日次 ETL）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env またはデフォルトから解決されます
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キー必要）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"スコアを書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

- カレンダー/営業日ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注:
- OpenAI 呼び出しを行う関数は api_key 引数で上書き可能（テスト時に差し替えやすい設計）。
- 日付処理はルックアヘッドバイアスを避けるよう設計されています（target_date を明示的に渡すことを推奨）。

---

## 自動環境変数読み込みについて
kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動的にロードします。  
自動ロードを無効化する場合:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env ファイルのパースはシェル風の export KEY=val 形式や引用符、インラインコメントに対応しています。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュール）
- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント集約 / score_news
  - regime_detector.py — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン / run_daily_etl 等
  - etl.py — ETLResult の公開
  - news_collector.py — RSS 収集・前処理・保存
  - calendar_management.py — market_calendar / 営業日判定 / calendar_update_job
  - quality.py — データ品質チェック
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- ai/regime_detector・news_nlp 等は OpenAI SDK を利用

（その他、execution / monitoring / strategy 等のサブパッケージがある想定で __all__ に含まれます）

---

## 開発・テスト
- テストを書くときは外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックしてください。  
  多くの内部呼び出しは _call_openai_api や _urlopen 等の関数を patch しやすい設計になっています。
- 環境に依存する自動環境ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化してください。

---

## 注意点 / 運用上のヒント
- 設定 `KABUSYS_ENV` は "development" / "paper_trading" / "live" のいずれかを指定してください（不正な値は例外になります）。
- OpenAI / J-Quants の API 呼び出しはコスト・レート制限があります。local 実行時や CI ではモックを活用してください。
- ETL は品質チェックを実行するとスキーマ不整合やデータ品質問題を検出できます。ETLResult に詳細を保持するので監査ログやアラートに利用してください。
- audit テーブル群は削除しない設計（監査ログ保持）。init_audit_db で初期化してください。

---

## ライセンス / 貢献
- 本プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください。  
- バグ報告・機能提案・プルリクエストは歓迎します。CI・テストカバレッジを追加してからの PR を推奨します。

---

README 作成時点の主な公開 API（参考）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.get_id_token(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db(...)
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day

必要であれば、各モジュールの詳細ドキュメント（関数引数・戻り値の詳細、サンプル SQL スキーマ、例外仕様など）も作成します。どの部分を優先して詳述したいか教えてください。