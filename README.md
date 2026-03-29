# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、因子計算、データ品質チェック、監査ログ（オーダー／約定追跡）など、投資システム構築に必要な共通機能を提供します。

---

## 特徴（機能一覧）

- 環境変数管理
  - `.env` / `.env.local` の自動読み込み（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
  - 必須項目は `kabusys.config.Settings` で取得（不足時に明確な例外）
- データ取得・ETL
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - 日次 ETL パイプライン（市場カレンダー / 株価日足 / 財務データ）
  - DuckDB への冪等的保存（ON CONFLICT を利用）
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip対応、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols テーブルへの冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースのバッチ評価（gpt-4o-mini + JSON Mode）
  - スコアのバリデーション・クリップ・リトライ実装
- 市場レジーム判定
  - ETF（1321）200日MA乖離（70%）とマクロニュースセンチメント（30%）を合成
  - LLM呼び出しはフェイルセーフ（失敗時 macro_sentiment = 0）
  - 判定結果を `market_regime` テーブルに冪等書き込み
- リサーチ / ファクター計算
  - Momentum / Value / Volatility 等のファクターを DuckDB のデータから算出
  - 将来リターン、IC（スピアマン）、統計サマリー 等のユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付整合性チェック（QualityIssue を返す）
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ
  - 発注フローのトレーサビリティ（UUID ベース、冪等キー）
- ユーティリティ
  - クロスセクション Z スコア正規化等の共通統計関数

---

## 必要条件 / 依存ライブラリ

主に以下が必要です（プロジェクトの pyproject.toml / requirements.txt に依存します）：

- Python 3.10+（型注釈の union shorthand 等を使用）
- duckdb
- openai
- defusedxml

その他、標準ライブラリ以外のネットワーク系・ユーティリティは上記パッケージに含まれます。

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

---

## 環境変数

主要な環境変数（必須のものは README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の Refresh Token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用の Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用可能）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（.git または pyproject.toml を基準にルートを探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（またはプロジェクトルートに .env を作成）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 必要に応じて OPENAI_API_KEY を設定

4. データベース用のディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要 API と実行例）

以下はライブラリを直接呼び出す例です。適宜ロギングや例外処理を追加してください。

- DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込み件数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すことも可（省略時は OPENAI_API_KEY を参照）
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 接続 conn を保持して監査テーブルが使用可能
```

- ファクター計算（リサーチ）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# momentum は dict のリスト（各要素に date, code, mom_1m, ... を含む）
```

- データ品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 実運用上の注意

- OpenAI API 呼び出しは料金発生とレート制限の対象です。バッチのサイズや頻度に注意してください。
- J-Quants API のレート制限（120 req/min）に合わせた RateLimiter を実装済みですが、複数プロセスで同一トークンを使う場合は外部でのレート管理を検討してください。
- DuckDB の executemany に空リストが指定できないバージョンの挙動に注意（コード内でガード済み）。
- モジュールはルックアヘッドバイアスを避ける設計方針で構築されています（内部で date.today() を直接参照しない等）。バックテスト時はデータの投入・保持順序に注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索します。テスト環境などで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下）

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
  - etl.py (ETL_result re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (プロジェクトには monitoring パッケージが __all__ に含まれている想定だが、ここに実装があれば配置)

上記のモジュール群はそれぞれ以下の責務を持ちます：

- config.py: 環境変数・設定管理（.env 読み込み）
- data/jquants_client.py: J-Quants API との通信と DuckDB 保存
- data/pipeline.py: 日次 ETL パイプライン実装（run_daily_etl 等）
- data/news_collector.py: RSS 取得・前処理・raw_news 保存
- ai/news_nlp.py: ニュースの LLM によるセンチメント評価（score_news）
- ai/regime_detector.py: マクロセンチメント + ETF MA によるレジーム判定（score_regime）
- research/*: ファクター計算・評価・統計ユーティリティ
- data/quality.py: 品質チェック
- data/audit.py: 監査ログスキーマ初期化

---

## 貢献・拡張ポイント（README補助）

- モデルやプロンプトの変更（OpenAI モデルの切替やプロンプト調整）
- ニュースソースの追加（DEFAULT_RSS_SOURCES）
- ETL のスケジューリング（cron / airflow など）や監視（Slack 通知）
- テスト: OpenAI / HTTP 呼び出し部分はモック可能な設計（内部 _call_openai_api や _urlopen を差し替え）

---

必要であれば、README に CI / テスト実行方法、より詳細な DB スキーマ（raw_prices/raw_news 等）や .env.example のテンプレート、サンプルジョブ（cron/systemd/airflow）の例を追記します。どの情報を補足しましょうか？