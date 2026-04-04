KabuSys
======

KabuSys は日本株向けのデータプラットフォーム兼自動売買リサーチ基盤です。  
DuckDB をデータレイヤに、J-Quants / RSS / OpenAI（LLM）を外部データソースとして利用し、ETL、データ品質チェック、ニュース NLP、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）を実装しています。

本 README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

プロジェクト概要
--------------
- 目的：日本株のデータ収集（J-Quants、RSS）、品質検査、特徴量生成（ファクター）、ニュースセンチメント解析（OpenAI）を統合し、戦略・実行・監視基盤を支える共通ライブラリ群を提供する。
- データ永続化：DuckDB を想定（設定でパス変更可）。
- フェイルセーフ設計：外部 API の失敗を局所化して全体停止を避ける実装（多くの箇所でフォールバックやゼロスコア化を行います）。
- Look-ahead bias 回避：バックテスト・解析で未来情報を参照しない設計（多くの関数が target_date を受け取り、現在時刻を直接参照しない）。

主な機能一覧
--------------
- 環境設定読み込み / settings（.env 自動読み込みを含む）
- J-Quants クライアント（株価、財務、カレンダー等の取得・DuckDB 保存）
- ETL パイプライン（run_daily_etl 等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS → raw_news、SSRF対策・URL正規化）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアの算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 研究 (research) モジュール（モメンタム・バリュー・ボラティリティ計算、IC、forward returns、z-score 正規化）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）
- 小規模監視設定（PID / kill flag / リソース閾値）

セットアップ手順
----------------

1. Python のバージョン
   - Python 3.10+ を推奨（typing, match などの理由より）。コードは 3.10+ の構文を想定しています。

2. 仮想環境作成（任意）
   - venv を推奨:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

3. 必要パッケージ（例）
   - 最低限の依存例（プロジェクトの setup/requirements がある場合はそれに従ってください）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 他に標準ライブラリのみで実装されている部分もありますが、実運用では logging 等の設定や HTTP 依存管理を行ってください。

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を配置すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化

   - .env.example を参考に作成してください（リポジトリに例ファイルがあればそれを利用）。

使い方（主要API例）
------------------

以下はコードから直接呼び出す例です。CLI ではなくライブラリとして利用する想定です。

1) DuckDB 接続準備
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) ETL（日次パイプライン実行）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行します。失敗は個別に捕捉され、ETLResult に記録されます。

3) ニュースセンチメント（銘柄別）取得
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20))
print("書込み銘柄数:", n_written)
```
- OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY を使用します。
- 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC 変換済み）

4) 市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```
- ETF 1321 の 200 日 MA とマクロニュース（LLM）の加重合成で label(bull/neutral/bear) を market_regime テーブルへ保存します。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY。

5) 監査ログスキーマ初期化（監査専用 DB を作る）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を監査ログ用に利用
```

6) RSS フェッチ単体（ニュースコレクタ）
```
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```
- SSRF 対策、トラッキングパラメータ除去、XML parsing の安全化（defusedxml）等が組み込まれています。

主要モジュールと簡単な説明
------------------------
- kabusys.config: .env / 環境変数の読み込み、settings オブジェクト（アプリ設定）
- kabusys.data.jquants_client: J-Quants API 呼び出し、取得・DuckDB への保存関数（save_*）
- kabusys.data.pipeline: ETL パイプライン（run_daily_etl など）と ETLResult
- kabusys.data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- kabusys.data.news_collector: RSS 収集・正規化・DB 保存の補助ロジック
- kabusys.data.calendar_management: 市場カレンダー管理・営業日取得ユーティリティ
- kabusys.data.audit: 監査ログ（signal_events / order_requests / executions）の DDL + 初期化
- kabusys.ai.news_nlp: ニュースを銘柄ごとにまとめて LLM に送り ai_scores へ保存
- kabusys.ai.regime_detector: ETF MA とマクロニュースを合成して market_regime を生成
- kabusys.research: factor 計算・特徴量探索（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）
- kabusys.data.stats: zscore_normalize 等の汎用統計ユーティリティ

ディレクトリ構成（主要ファイル）
--------------------------------
（リポジトリ内 src/kabusys を起点に抜粋）

- src/kabusys/
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
    - etl.py  (pipeline の再エクスポート)
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - (その他: db 初期化・クライアント補助など)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor/IC/summary 関数群）

注意点 / 実運用のヒント
---------------------
- OpenAI 使用時はレスポンスの JSON フォーマット検証やリトライロジックが実装されていますが、API 使用制限やコスト管理は運用側で注意してください。
- J-Quants API はレート制限を守るため内部でスロットリング（RateLimiter）を行います。ID トークンは自動リフレッシュされます。
- ETL 実行中に一部ステップが失敗しても他ステップは継続され、ETLResult.errors にエラー概要が記録されます。運用スクリプトでログと ETLResult を監視してください。
- データベーススキーマやインデックスは監査初期化関数（init_audit_schema）で作成します。既存 DB に対して冪等に適用されます。
- テストや CI で .env の自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル：最小起動スクリプト
-------------------------
簡易的な日次 ETL + ニュース解析を行うスクリプト例：

```
#!/usr/bin/env python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl
from kabusys.ai.news_nlp import score_news

def main():
    conn = duckdb.connect(str(settings.duckdb_path))
    etl_result = run_daily_etl(conn, target_date=date.today())
    print("ETL:", etl_result.to_dict())
    n = score_news(conn, target_date=date.today())
    print("News scored:", n)

if __name__ == "__main__":
    main()
```

最後に
-----
この README はコードベースに内包されたドキュメント（モジュール docstring）を基に作成しています。さらに詳しい仕様（API レスポンスフィールド、DB スキーマの完全定義、運用手順）はプロジェクトの設計ドキュメント（StrategyModel.md, DataPlatform.md 等）や .env.example を参照してください。必要であれば README に含める追加サンプルや CI / デプロイ手順を作成しますのでご依頼ください。