KabuSys
======

KabuSys は日本株のデータ基盤・リサーチ・AIスコアリング・監査ログ・ETL・市場レジーム判定を含む自動売買／研究プラットフォームのコアライブラリです。本リポジトリは DuckDB をバックエンドに用いたデータパイプライン、J-Quants API クライアント、OpenAI を用いたニュースセンチメント／市場レジーム判定、各種ファクター計算やデータ品質チェック、監査ログスキーマなどを提供します。

主な特徴
-----
- データ取得 / ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・レート制御・リトライ対応）
  - ETL の結果を ETLResult として集約
- データ品質管理
  - 欠損、重複、スパイク、日付不整合などの品質チェック機能（quality モジュール）
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini） を用いた銘柄ごとのニュースセンチメントスコアリング（news_nlp）
  - マクロニュースと ETF（1321）200 日移動平均乖離を組み合わせた市場レジーム判定（regime_detector）
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - クロスセクション Z スコア正規化など
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定の監査テーブル定義および初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（自動ロードを環境変数で無効化可能）

必須機能一覧（抜粋）
-----
- kabusys.config.Settings：環境変数による設定管理（自動 .env ロード）
- kabusys.data.jquants_client：J-Quants API クライアント（取得・保存関数）
- kabusys.data.pipeline：日次 ETL 実行 run_daily_etl 等
- kabusys.data.quality：品質チェック群（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- kabusys.data.news_collector：RSS 取得・前処理（fetch_rss 等）
- kabusys.ai.news_nlp.score_news：銘柄ごとのニューススコアリング
- kabusys.ai.regime_detector.score_regime：市場レジーム判定（ma200 + マクロニュース）
- kabusys.research：ファクター計算・探索（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等）
- kabusys.data.audit：監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.data.stats.zscore_normalize：Z スコア正規化ユーティリティ

セットアップ手順
-----

前提
- Python 3.10+（typing の | 合成などを使用）
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例（仮の requirements）
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# 開発時は -e でインストールできるようパッケージ化している場合は pip install -e .
```

環境変数 / .env
- プロジェクトルート（pyproject.toml または .git がある場所）に .env/.env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
- 主な環境変数（Settings 参照）:
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite (監視用)（デフォルト data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を呼ぶ際に省略可。関数引数で上書き可能）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

データベース初期化
- 監査 DB を作成してスキーマを初期化する例：
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル signal_events, order_requests, executions 等が作成されます
```

使い方（主要フロー）
-----

1) 日次 ETL 実行（価格・財務・カレンダー収集 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が環境に必要
print(f"scored {n} codes")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュース合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算 / 研究用ユーティリティ例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

5) RSS ニュース取得（前処理）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 返り値は前処理済みの NewsArticle 型リスト
```

設計上の注意点 / 実装方針
-----
- Look-ahead bias に対する配慮（関数は内部で datetime.today() を参照しない、target_date 引数で明示的に指定）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で行う設計
- 外部 API 呼び出し（OpenAI / J-Quants）にはリトライ・バックオフ・レート制御を組み込む
- ニュース収集では SSRF や XML 攻撃対策（defusedxml、リダイレクト検査、ホストのプライベート判定）を実施
- OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーションを厳密に行う（不正時はフェイルセーフでスコア 0 等にフォールバック）

ディレクトリ構成（主要ファイル）
-----
- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄ごと）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult など）
    - news_collector.py      — RSS 収集 / 前処理
    - calendar_management.py — JPX カレンダー管理 / 営業日ロジック
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマと初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / rank / summary
  - research/ ... その他ユーティリティ
  - その他（monitoring / execution / strategy 等のパッケージが __all__ に含まれる想定）

追加情報 / 運用メモ
-----
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時や特殊な環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワークエラーやレート制限に対して堅牢な設計ですが、API キーとトークンは適切に管理してください。
- DuckDB を使っているためデータファイルは単一ファイルで管理できます（バックアップやバージョン管理に注意）。
- 監査ログは削除しない前提で設計されています。必要に応じてバックアップやローテーションを検討してください。

貢献 / テスト
-----
- 各外部 API 呼び出しは内部で差し替え可能に実装されており、単体テスト時はモック化して振る舞いを検証できます（例: kabusys.ai.news_nlp._call_openai_api のパッチなど）。
- 新しい ETL / 保存ロジックは小さな単位で関数化し、品質チェックを追加してください。

お問い合わせ
-----
問題点・改善提案や使用上の質問がある場合はリポジトリ管理者へお問い合わせください。

---
（この README はコードベースの docstring と実装から生成しました。実際の運用環境に合わせて .env.example、requirements.txt、起動スクリプト等を整備してください。）