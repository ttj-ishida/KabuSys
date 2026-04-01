KabuSys — 日本株自動売買システム
==============================

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）算出、ニュースの LLM ベース評価、マーケットレジーム判定、監査ログ（オーディット）等を含む自動売買基盤のライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API / RSS / OpenAI（LLM）等と連携することで、研究（Research）と実行（Execution）に必要な機能群を提供します。

主な特徴
--------
- ETL パイプライン
  - J-Quants から株価（日足）・財務・マーケットカレンダーを差分取得して DuckDB に冪等保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行
- ニュース分析（LLM）
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）によりセンチメント（ai_score）を生成（score_news）
  - マクロ経済ニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）（score_regime）
- 研究ユーティリティ
  - モメンタム、バリュー、ボラティリティ等のファクター算出（calc_momentum, calc_value, calc_volatility）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等（calc_forward_returns, calc_ic, factor_summary など）
  - Zスコア正規化ユーティリティ（zscore_normalize）
- ニュース収集
  - RSS フィード収集（SSRF対策、URL 正規化、トラッキングパラメータ除去）
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までをトレースする監査テーブルを DuckDB に初期化・管理
- 設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート判定: .git または pyproject.toml）および環境変数での設定

セットアップ
-----------

前提
- Python 3.10+
- DuckDB（Python パッケージ）、OpenAI Python SDK、defusedxml などが必要

推奨インストール（開発環境・ローカル）
1. 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate (UNIX/macOS)
2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

プロジェクトを pip editable インストールする場合:
- pip install -e .

環境変数
- 自動読み込み:
  - パッケージ import 時にプロジェクトルートが検出されれば .env → .env.local の順で自動ロードします。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（主要）環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（必要なら）
- SLACK_CHANNEL_ID       : Slack チャネル ID（必要なら）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（必要なら）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector に必要）

その他（デフォルトあり）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH          : 実行 PIDファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV            : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL              : DEBUG|INFO|...（デフォルト: INFO）

簡易 .env.example（プロジェクトルート）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な利用例）
--------------------

1) 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

2) DuckDB 接続を開いて日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコア算出（AI）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定されている想定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログスキーマ初期化（オーディット DB）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を保持して監査ログの操作に利用
```

6) 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
from datetime import date

momentum_records = calc_momentum(conn, target_date=date(2026, 3, 20))
vol_records = calc_volatility(conn, target_date=date(2026, 3, 20))
value_records = calc_value(conn, target_date=date(2026, 3, 20))

# Z-score 正規化
normalized = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "ma200_dev"])
```

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 内の主要モジュール一覧（抜粋）です。

- __init__.py
- config.py
  - 環境変数・.env 自動読み込み・設定オブジェクト（settings）
- ai/
  - news_nlp.py         : ニュースの LLM センチメント算出（score_news）
  - regime_detector.py  : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（fetch / save / auth）
  - pipeline.py         : ETL パイプライン（run_daily_etl 等）
  - etl.py              : ETLResult 再エクスポート
  - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py   : RSS フィード収集・前処理
  - quality.py          : データ品質チェック
  - stats.py            : zscore_normalize 等の統計ユーティリティ
  - audit.py            : 監査ログ（テーブル初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py  : calc_momentum / calc_value / calc_volatility
  - feature_exploration.py : calc_forward_returns / calc_ic / factor_summary / rank
- ai/__init__.py
- research/__init__.py

注意点・設計方針
----------------
- ルックアヘッドバイアス対策:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照しないように設計されています。target_date を明示的に渡して使用してください。
- 冪等性:
  - J-Quants の保存関数や監査ログの初期化等は冪等に実装されています（INSERT ... ON CONFLICT）。
- フェイルセーフ:
  - OpenAI 呼び出しや外部 API 呼び出しは失敗時に安全なフォールバック（スコア 0.0、部分スキップ）を行う設計です。
- セキュリティ:
  - RSS 取得では SSRF 対策（リダイレクト検査、プライベートホスト拒否）、defusedxml を使用しています。

依存ライブラリ（主なもの）
------------------------
- duckdb
- openai
- defusedxml

（実際の requirements.txt / pyproject.toml を参照してください）

開発・テスト
------------
- 自動 .env ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。ユニットテスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化すると安定します。
- OpenAI / J-Quants の外部呼び出しはテストでモック化できるよう設計されています（モジュール内の _call_openai_api 等を patch）。

ライセンス・貢献
----------------
- リポジトリの LICENSE や CONTRIBUTING.md を参照してください。

問い合わせ
----------
問題・改善提案は issue を立てるか、開発チームへ連絡してください。

---

この README はコードベースのソースと docstring に基づいて作成しています。追加の利用方法や運用手順（デプロイ、監視、バックテスト統合など）はプロジェクトのドキュメントを参照してください。