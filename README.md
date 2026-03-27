# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、品質チェック、ETL、ニュースセンチメント（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPXマーケットカレンダー取得（ページネーション・率制御・リトライ実装）
  - 差分更新・バックフィル対応の ETL パイプライン（run_daily_etl 等）
  - データ保存は DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- データ品質管理
  - 欠損値、重複、スパイク、日付不整合のチェック（quality モジュール）
  - 品質チェックの集約実行（run_all_checks）

- ニュース収集 & NLP
  - RSS フィードからニュースを収集して raw_news に保存（SSRF/サイズ/トラッキング対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメントスコアリング（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA200乖離から市場レジームを判定（ai.regime_detector.score_regime）

- リサーチ / ファクター計算
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research）
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Zスコア正規化（data.stats / research.feature_exploration）

- 監査ログ（トレーサビリティ）
  - signal -> order_request -> execution の階層で監査テーブルを提供（data.audit）
  - 監査DB初期化ユーティリティ（init_audit_db / init_audit_schema）

- 設定管理
  - .env ファイルまたは環境変数から設定を自動ロード（config）
  - 自動ロードはプロジェクトルート（.git or pyproject.toml）基準。無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

---

## 必要な依存パッケージ（主なもの）

- Python 3.9+
- duckdb
- openai
- defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置

2. Python 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env` を配置することで自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY
   - オプション:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

例 `.env`（最小）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB ファイルの初期化（監査ログ用など）
   - Python API から実行できます（下欄 使い方 参照）。

---

## 使い方（主要 API の利用例）

以下は Python スクリプト/REPL での利用例です。

共通準備:
```python
import duckdb
from kabusys.config import settings
```

DuckDB 接続（デフォルトパスを使用）:
```python
conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次ETL 実行）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントを生成（OpenAI API キーは OPENAI_API_KEY を使用）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print("scored codes:", count)
```

市場レジームを判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査DB（監査ログ）を初期化して接続を得る:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

ファクター計算（リサーチ）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

マーケットカレンダーのユーティリティ:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
is_trade = is_trading_day(conn, d)
next_trade = next_trading_day(conn, d)
```

設定の自動ロードを抑止したい（テスト等）:
環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールをインポートしてください。

---

## よく使う内部挙動の注意点（設計上のポイント）

- Look-ahead バイアスの防止: モジュールの多くが date / target_date を明示的に受け取り、内部で datetime.today() を直接参照しません。
- OpenAI 呼び出し: JSON mode（response_format={"type":"json_object"}）を使い、レスポンス検証やリトライを実装しています。
- J-Quants クライアント: レート制限のため固定間隔スロットリング、401 時のトークン自動更新、ページネーション対応を行います。
- DuckDB 操作: 多くの書込処理は冪等（ON CONFLICT DO UPDATE）です。executemany に空リストを渡すと問題になるバージョンを想定してガードしています。
- ニュース収集: SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去、gzip 解凍保護などを実装しています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数・設定管理、.env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 外部インターフェース再エクスポート
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py — RSS ニュース収集
  - quality.py — データ品質チェック
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/__init__.py, research/__init__.py などで主要関数を公開

---

## テスト・開発上のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化できます。
- OpenAI・J-Quants の外部API呼び出しはユニットテストでモックすることを推奨します。内部では _call_openai_api などの関数を簡単にパッチ可能に設計しています。
- DuckDB は軽量なためテストでは ":memory:" を使うことでインメモリ DB を利用できます（init_audit_db(":memory:") 等）。

---

この README はコードベースの主要機能と使い始めに必要な情報をまとめたものです。詳細な API の仕様や運用手順は各モジュールの docstring を参照してください。