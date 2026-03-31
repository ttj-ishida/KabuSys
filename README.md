# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータパイプライン、AI によるニュースセンチメント、ファクター計算、監査ログなどを備えた自動売買／リサーチ基盤の Python ライブラリ群です。本リポジトリは ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレース）の初期化・操作などを提供します。

主な用途
- J-Quants からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたローカルデータベース管理
- ニュースの収集・前処理・LLM によるセンチメント評価
- マーケットレジーム判定（MA と マクロニュースの組合せ）
- ファクター計算・特徴量探索（リサーチ用途）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注/シグナルの監査ログ（監査テーブル初期化）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークン更新・ページネーション・レートリミット対応）
  - market_calendar の管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、トラッキング除去）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を用いた JSON モード呼び出し、リトライ・フェイルセーフ設計
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、ランク化

---

## 必要条件

- Python 3.10 以上（typing の | 型注釈などを使用）
- 推奨パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI を利用する場合）
- J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- OpenAI API キー（OPENAI_API_KEY） — AI 機能を使う場合

インストール例（仮）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発中なら:
# pip install -e .
```

（プロジェクト配布に requirements.txt / pyproject.toml がある想定であればそれに従ってください）

---

## 環境変数 / 設定

プロジェクトは .env/.env.local または OS 環境変数を読み込みます（自動ロード、プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（settings にアクセス可能なプロパティ名と対応）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用途）ファイルパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（数値）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を呼ぶ際に利用）

注意: Settings の必須項目が未設定の場合、プロパティアクセス時に ValueError が発生します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # または開発用なら: pip install -e .
   ```

4. .env を作成（.env.example を参考に必要なキーを設定）
   - 必須例:
     - JQUANTS_REFRESH_TOKEN=
     - OPENAI_API_KEY=            # AI 機能利用時
     - SLACK_BOT_TOKEN=
     - SLACK_CHANNEL_ID=
     - KABU_API_PASSWORD=
     - (必要に応じて) DUCKDB_PATH 等

5. DuckDB ファイルやデータディレクトリの作成（自動で作られる場合もありますが確認）
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は主要な機能を呼び出す際の簡単なコード例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB 接続を作って ETL を実行する（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定していれば api_key=None で良い
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組合せ）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化（独立 DB を作る）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path の代わりに監査専用パスを渡すことも可能
audit_conn = init_audit_db(settings.duckdb_path)
# audit_conn は DuckDB 接続。テーブルが作成されます。
```

- ファクター計算・研究関数の呼び出し
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

---

## 自動ロードとテスト時の扱い

- config モジュールはパッケージの起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。
- テストや一時的に自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## 実装上の注意点 / 設計方針（抜粋）

- Look-ahead バイアス対策: 多くの関数で内部で date.today() を不用意に参照せず、呼び出し側で基準日（target_date）を渡す設計になっています。
- ETL / AI 呼び出しはフェイルセーフ: 一部 API 呼び出し失敗時にはスコアを 0.0 にフォールバックしたり、処理をスキップして継続する設計です（例: OpenAI の一時的失敗やレスポンスパース失敗）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ニュース収集は SSRF 対策やレスポンスサイズ上限、トラッキングパラメータ除去などの安全対策を含みます。
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを実装しています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリが src/kabusys 構成を持つ想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLU / スコアリング
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 共通統計ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — IC / forward returns / summary
  - research/（その他ユーティリティ）
- pyproject.toml / setup.cfg / .gitignore （プロジェクトルート）

---

## 開発・テスト時のヒント

- OpenAI 呼び出しやネットワーク依存処理はユニットテストでモック可能なように設計されています（内部の _call_openai_api や network opener をパッチする）。
- DuckDB はインメモリ（":memory:"）で接続できるため、テスト用 DB として利用すると高速で便利です。
- ETL 実行後は data.quality.run_all_checks を使って品質問題のサマリを取得できます。

---

## 最後に

この README はコードベースの主要機能と基本的な使い方をまとめたものです。各モジュール内に豊富なドキュメント文字列（docstring）が存在しますので、より詳細な挙動・例外仕様は該当ファイルを参照してください。追加の使い方やサンプルスクリプトが必要であればお知らせください。