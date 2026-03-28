# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。  
J-Quants や RSS、OpenAI（LLM）を使ったデータ取得・品質管理・AI スコアリング・ファクター計算・監査ログなど、トレードシステムの主要なコンポーネントを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスを排除する（内部で date.today()/datetime.today() を勝手に参照しない）
- DuckDB をデータ基盤に利用し、効率的な SQL / ウィンドウ集計処理を行う
- 外部 API 呼び出しはリトライ / フェイルセーフを実装（J-Quants, OpenAI 等）
- ETL / 品質チェックは部分失敗を許容して可能な限り進める（Fail-Fast ではない）
- 監査ログでシグナル→発注→約定までトレーサビリティを確保

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート判定）
  - 必須設定チェックを行う Settings API
- データ取得・ETL（J-Quants）
  - 株価日足（raw_prices / prices_daily）
  - 財務データ（raw_financials）
  - JPX マーケットカレンダー（market_calendar）
  - レート制限・リトライ・ID トークン自動更新対応
- ニュース収集
  - RSS フィード取得・前処理（URL 正規化、SSRF 対策、Gzip の扱い等）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント（ai_scores へ保存）
  - マクロニュースを使った市場レジーム判定（market_regime へ保存）
  - バッチ・リトライ・レスポンス検証
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等の定量ファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）
- マーケットカレンダー管理
  - 営業日判定 / next/prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants から差分取得して保存）
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db / init_audit_schema（DuckDB）を提供

---

## セットアップ手順

前提:
- Python 3.10+（typing | 複数の型注釈を使用）
- DuckDB, OpenAI クライアント等の依存パッケージ

推奨インストール（例）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt があればそれを利用してください）

環境変数 / .env の準備:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（README では必須・主なものを列挙）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime の引数でも指定可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

.example .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

共通：DuckDB 接続を作成して関数に渡す例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（AI）でスコアを付与し ai_scores を更新
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

3) マーケットレジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用の DuckDB 初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルに記録可能
```

5) カレンダー操作（営業日判定など）
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))
```

6) リサーチ（ファクター計算例）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

ログ出力レベルは環境変数 `LOG_LEVEL` で調整してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py               - ニュース NLP（銘柄ごとのスコアリング）
    - regime_detector.py        - マクロ + ETF による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント（取得 + 保存）
    - pipeline.py               - ETL パイプライン（run_daily_etl 等）
    - etl.py                    - ETL の公開型定義（ETLResult）
    - news_collector.py         - RSS 収集・前処理
    - calendar_management.py    - マーケットカレンダー管理
    - quality.py                - データ品質チェック
    - stats.py                  - 統計ユーティリティ（zscore 等）
    - audit.py                  - 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py        - ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py    - 将来リターン / IC / 統計サマリー 等
  - ai、data、research 以下にさらに補助関数群あり

主要な DB テーブル（コード内で参照されるもの）
- raw_prices / prices_daily
- raw_financials
- raw_news / news_symbols
- ai_scores
- market_calendar
- market_regime
- signal_events / order_requests / executions（監査ログ）

---

## テスト・デバッグのヒント

- OpenAI / J-Quants 呼び出しはリトライやフェイルセーフ実装がありますが、ユニットテストでは外部呼び出しをモックすることを推奨します（コード中にも unittest.mock.patch を想定した差し替えポイントがあります）。
- 自動 .env ロードはプロジェクトルート探索 (.git / pyproject.toml) に依存します。テストで環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要な環境変数をプログラム内で注入してください。
- DuckDB に接続しているときは DuckDB の SQL を直接実行してテーブル内容を確認できます（例: conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()）。

---

## ライセンス・貢献

この README はコードベースの説明用です。実際のライセンスや貢献方法はリポジトリの LICENSE / CONTRIBUTING ファイルに従ってください。

---

もし README に追加したい具体的な実行コマンド（例: systemd ユニット、airflow タスク、cron ジョブ）や CI/CD のセットアップ、より詳細な .env.example を望む場合はお知らせください。