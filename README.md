# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定トレース）、および市場レジーム判定などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない実装）
- DuckDB をデータストアとして利用し、ETL は冪等（ON CONFLICT）で実装
- 外部 API（J-Quants / OpenAI）呼び出しはリトライやレート制御を備えフェイルセーフ化

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（pagination 対応、レート制御・リトライ・トークン自動リフレッシュ）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次のレジーム判定（score_regime）
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算、Z スコア正規化等
- 監査ログ
  - signal_events / order_requests / executions を含む監査スキーマ初期化（init_audit_schema/init_audit_db）
- 設定管理
  - 環境変数または .env(.env.local) の自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## 前提・依存

- Python 3.10+
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

インストール例：
pip install duckdb openai defusedxml

（プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置することで自動読み込みされます（優先順：OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例：.env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...

設定項目と説明（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: execution 環境。development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

---

## 使い方（コード例）

以下は Python REPL やスクリプトから利用する最小例です。

- DuckDB 接続を作成して ETL を実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"scored {n} symbols")
```

- 市場レジームスコア計算
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ファイルパスを指定して DuckDB を初期化
```

- RSS をフェッチ（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## テスト／デバッグのヒント

- 自動 .env 読み込みを無効にする
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をエクスポートしてテスト時に環境変数を明示的に設定できます。
- OpenAI / J-Quants 呼び出しはネットワークを伴うため、unittest.mock.patch で _call_openai_api や jquants_client._request を差し替えて単体テストを実施できます（コード内に差し替えを想定したコメントあり）。
- DuckDB のインメモリ接続は db_path=":memory:" を使えます（audit.init_audit_db 等でサポート）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定の管理 (.env 自動読み込み)
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLU / スコアリング（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             - J-Quants API クライアント（fetch_*, save_*）
    - news_collector.py             - RSS 収集 / 正規化
    - calendar_management.py        - 市場カレンダー管理（is_trading_day 等）
    - quality.py                    - データ品質チェック（QualityIssue）
    - stats.py                      - 共通統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化
    - pipeline.py                   - ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py            - Momentum/Value/Volatility ファクター
    - feature_exploration.py        - 将来リターン・IC・統計サマリー
  - monitoring/ (該当コードは一部モジュールで参照)
  - execution/ (発注実装は別モジュール想定)
  - strategy/ (戦略関連コード想定)

（README はコードベースの抜粋に基づき作成しています。実際のリポジトリにはさらにモジュールやユーティリティが含まれる場合があります）

---

## 注意事項

- OpenAI / J-Quants の API キー・トークンは必ず安全に保管し、公開リポジトリに含めないでください。
- 実口座での実行はリスクを伴います。paper_trading 環境を利用して十分に検証してください（KABUSYS_ENV=paper_trading）。
- 本 README はコードスニペットから生成しています。実際に利用する際はプロジェクトの pyproject.toml / requirements.txt / .env.example 等を参照してください。

---

ご希望があれば、README に CLI 実行例（スクリプト化）や .env.example のテンプレート、systemd / cron 用の実行例、もっと詳細なモジュール一覧を追加します。