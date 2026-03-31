# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログスキーマ、マーケットカレンダー管理などを含みます。

主に DuckDB を内部データストアとして利用し、OpenAI（gpt-4o-mini）によるニュースセンチメント評価や J-Quants API との連携を前提とした設計になっています。

---

## 主要な機能

- データ取得・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存（冪等保存）。
  - ETL の実行結果を ETLResult で集約し、品質チェックを実行可能。

- ニュース収集・NLP
  - RSS フィードから安全を考慮してニュースを収集し raw_news に保存。
  - OpenAI を使った銘柄別ニュースセンチメント算出（ai_scores へ書込）。
  - ニュースのタイムウィンドウ管理（JST 基準）やトークン肥大化対策、バッチ処理、堅牢なレスポンス検証／リトライ実装。

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して market_regime を日次判定。

- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ

- カレンダー / 監査
  - JPX マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ（signal_events, order_requests, executions）用スキーマの初期化ユーティリティ

- データ品質チェック
  - 欠損・スパイク・重複・将来日付／非営業日データの検出

---

## 要件

- Python >= 3.10
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等も使用

（必要なパッケージはプロジェクトの requirements ファイルや pyproject.toml を参照してください。ここではコードで利用している主要ライブラリを挙げています。）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

4. パッケージをインストール（編集可能モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます（モジュール kabusys.config による自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の主な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注連携等）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で使用）

オプション / デフォルト例
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live), default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL), default: INFO

例 .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化例

監査ログ用スキーマを初期化する例:

```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可
# 以降 conn を用いて監査ログ操作が可能
```

DuckDB を既存 path で使う場合:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 必要な場合はスキーマ初期化関数を呼ぶ (集約スキーマ等を用意する別関数があればそれを実行)
```

---

## 使い方（代表的な API）

- 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {written} scores")
```

- 市場レジームスコアを算出して market_regime に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- カレンダーの夜間バッチ更新ジョブ

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

- 研究用: ファクター・IC 計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
forwards = calc_forward_returns(conn, target_date=date(2026,3,20))
# calc_ic や zscore_normalize 等を使って解析
```

---

## 自動環境変数読み込みの挙動

- kabusys.config モジュールは起動時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
  - 優先順位: OS環境変数 > .env.local > .env
  - OS 環境変数は保護（上書きされません）
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py  — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL 結果型の再エクスポート
    - news_collector.py   — RSS ベースのニュース収集
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン／IC／統計サマリー
  - ai/（上記）
  - その他: strategy, execution, monitoring（パッケージ公開名に含まれるが、各機能はコードベースの別ファイルに実装されます）

（詳細は各モジュールの docstring を参照してください。各モジュールは設計方針やフェイルセーフ挙動についてコメントで詳述されています。）

---

## 設計上の注意点・運用メモ

- Look-ahead バイアス対策:
  - 各モジュールは内部で date.today() や datetime.today() を直接参照しないよう配慮し、必ず target_date を明示的に渡すことで過去情報のみを参照する設計になっています。
- OpenAI / J-Quants 呼び出し:
  - リトライやバックオフ、API エラー時のフォールバックが実装されています。API キーの管理に注意してください。
- DuckDB の executemany に対する互換性や空リストの扱いに注意した実装になっています（部分書き込み戦略で部分失敗時のデータ保護を実現）。
- news_collector は SSRF 対策（プライベートIP拒否、リダイレクト検査）や XML パースの安全化（defusedxml）を行っています。

---

## 貢献・拡張

- 新しい ETL データや API エンドポイントの追加は data/jquants_client.py に fetch/save 関数を追加し、pipeline.run_* の流れに組み込んでください。
- ニュースソースの追加は data/news_collector.DEFAULT_RSS_SOURCES を拡張してください。
- 研究用モジュールは pure-Python で記述しているため、分析用の拡張やユニットテストが容易です。

---

必要に応じて README を追記します（例: テスト手順、CI 設定、実運用時のデプロイガイド、Slack / 発注ワークフローの説明など）。追加してほしい内容があれば教えてください。