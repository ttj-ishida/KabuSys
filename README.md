KabuSys — 日本株自動売買プラットフォーム
================================

概要
----
KabuSys は日本株のデータ取得（J‑Quants）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、ETL、データ品質チェック、監査ログ等を備えた研究／自動売買プラットフォームのライブラリ群です。  
DuckDB をデータ基盤として利用し、J‑Quants API と OpenAI（gpt‑4o‑mini）を外部サービスとして組み合わせる設計になっています。

主な特徴
--------
- J‑Quants からの差分 ETL（株価日足 / 財務 / マーケットカレンダー）と保存（冪等）
- RSS ベースのニュース収集と記事前処理（SSRF 防止、トラッキングパラメータ除去）
- OpenAI を使ったニュースセンチメント解析（銘柄別）とマクロセンチメント評価
- 日次 ETL パイプライン（品質チェック付き）と個別 ETL ヘルパー
- ファクター計算（Momentum / Value / Volatility 等）と研究用統計ツール
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions）のスキーマ生成と初期化
- 環境変数ベースの設定管理（.env / .env.local の自動読み込み、無効化オプションあり）

セットアップ
-----------

前提
- Python 3.10 以上（typing の | 記法を使用）
- pip, virtualenv 等の環境管理ツール

1) リポジトリをクローン／パッケージをインストール
- 開発中の場合:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install -e .            （パッケージ化されている場合）
- もしくは必要最小パッケージを直接インストール:
  - pip install duckdb openai defusedxml

2) 必要な環境変数を設定
プロジェクトは .env / .env.local（プロジェクトルート：.git または pyproject.toml を探索）を自動で読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使用する SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

（.env.example を参考に .env を作成してください）

使い方（基本例）
---------------

以下はライブラリ関数を直接呼ぶシンプルな例です。プロダクションでは各関数の戻り値や例外を適切に処理してください。

1) DuckDB 接続の用意
- デフォルトのパスは settings.duckdb_path（設定で変更可）。
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコア（銘柄別）を生成
- OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で指定できます。
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

4) 市場レジーム判定（ETF 1321 の MA とマクロニュースを組合せ）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査用 DuckDB）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使うか別ファイルを指定
audit_conn = init_audit_db(settings.duckdb_path)
```

6) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

補足:
- news_nlp.score_news / regime_detector.score_regime は OpenAI 呼び出しを伴います。API キーやコスト・リトライの考慮を行ってください。
- ETL / 保存関数は冪等（ON CONFLICT DO UPDATE）を意識して設計されています。

設定管理の注意点
----------------
- .env / .env.local はプロジェクトルートに置くと自動読み込みされます。自動読み込みを阻止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- 必須の値が欠けている場合、kabusys.config.Settings のプロパティアクセスで ValueError が発生します。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定してください。

主要ディレクトリ構成
-------------------
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数・設定管理、.env 自動読み込み)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースの銘柄別センチメントスコア)
    - regime_detector.py  (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J‑Quants API クライアント + DuckDB 保存)
    - pipeline.py         (ETL パイプラインと run_daily_etl)
    - etl.py              (ETL 結果データクラス再エクスポート)
    - news_collector.py   (RSS 収集・前処理・保存)
    - calendar_management.py (市場カレンダー管理・営業日判定)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ: zscore 正規化等)
    - audit.py            (監査ログスキーマ生成・初期化)
  - research/
    - __init__.py
    - factor_research.py      (Momentum/Value/Volatility 等)
    - feature_exploration.py  (forward returns, IC, factor_summary, rank)

開発・デバッグのヒント
---------------------
- ログレベルは環境変数 LOG_LEVEL で設定可能（デフォルト INFO）。
- DuckDB の一時検証やクエリ実行は duckdb.connect(":memory:") でインメモリ DB を利用できます。
- OpenAI 呼び出しはテストでモック可能（各モジュール内の _call_openai_api を patch）。
- .env ファイルの自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml を基準）。

ライセンス・貢献
----------------
（リポジトリに LICENSE があればそこを参照してください）

その他
-----
この README はコードベース（src/kabusys 以下）の説明に基づき作成しています。各関数・クラスの詳細な仕様や追加のユーティリティはソース内の docstring を参照してください。質問や具体的な利用例（例: バックテストとの連携、運用時のジョブスケジュール例）については追加で補足できます。