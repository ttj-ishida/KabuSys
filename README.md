KabuSys
======

日本株向けのデータプラットフォーム兼自動売買／リサーチ基盤ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants / RSS / OpenAI 等と連携して ETL、データ品質チェック、ニュースセンチメント、マーケットレジーム判定、ファクター計算、監査ログなどの機能を提供します。

注意: このリポジトリはライブラリ／基盤コードを中心に実装されています。実運用の前に環境変数や DB スキーマ、API キーの管理を必ず確認してください。

主な機能
-----

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー等の差分取得／保存（ページネーション・再試行・レート制御対応）
- ETL パイプライン
  - run_daily_etl を中心とする差分取得 → 保存 → 品質チェックの一括実行
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出する quality モジュール
- ニュース収集・NLP（OpenAI）
  - RSS からニュース収集（SSRF 対策・トラッキング除去）および gpt-4o-mini を用いた銘柄別センチメント算出（news_nlp.score_news）
- 市場レジーム判定（AI + テクニカル）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）、将来リターン計算、IC 計算、Z スコア正規化等
- 監査ログ（Audit）
  - シグナル → 発注 → 約定をUUIDベースでトレースする監査テーブルの初期化・管理（DuckDB）

セットアップ手順
-----

前提
- Python 3.10 以上（| 型注釈や新しい typing 機能を使用）
- システムに DuckDB 用のバイナリが無くても pip の duckdb で動作します

例: 仮想環境作成と依存インストール
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix)
   - .venv\Scripts\activate (Windows)
3. 必要パッケージのインストール（最小）
   - pip install duckdb openai defusedxml
   - （ローカル開発用に編集可能な場合）pip install -e .

環境変数
- .env（プロジェクトルート）または OS 環境変数から読み込まれます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートは .git または pyproject.toml を基準に探索します。

主要な環境変数（必須 / 任意）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime に未指定時に参照）
- DUCKDB_PATH           : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL             : ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）

使い方（簡単な例）
-----

基本的な流れ: DuckDB に接続して ETL → ニューススコア → レジーム判定 → 研究処理 などを呼び出します。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2）日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3）ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key を省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

4）市場レジーム判定（ma200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5）監査ログ用 DB 初期化（別ファイル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルに書き込みなどができる
```

6）研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 取得した dict リストを zscore_normalize 等で正規化して利用可能
```

主な公開 API / 関数一覧（抜粋）
- kabusys.data.pipeline.run_daily_etl(...) : 日次 ETL を一括実行
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar : J-Quants から取得
- kabusys.data.jquants_client.save_* : DuckDB への保存（冪等）
- kabusys.data.news_collector.fetch_rss(...) : RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) : 銘柄別ニューススコア生成
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) : 市場レジーム判定
- kabusys.research.factor_research.calc_momentum / calc_value / calc_volatility
- kabusys.data.quality.run_all_checks(...) : 品質チェック一括実行
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...) : 監査スキーマ初期化

ディレクトリ構成
-----

（パッケージ内の主要ファイル・モジュールの役割）
- src/kabusys/
  - __init__.py
  - config.py                    : 環境変数 / 設定の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                 : ニュースセンチメント算出（OpenAI 経由）
    - regime_detector.py         : マーケットレジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          : J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py                : ETL パイプライン（run_daily_etl 等）
    - etl.py                     : ETL 公開型（ETLResult 再エクスポート）
    - news_collector.py          : RSS 収集（SSRF 対策・正規化）
    - calendar_management.py     : 市場カレンダー管理（営業日判定、更新ジョブ）
    - quality.py                 : データ品質チェック
    - stats.py                   : 汎用統計ユーティリティ（zscore 正規化等）
    - audit.py                   : 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py         : ファクター計算（momentum, value, volatility）
    - feature_exploration.py     : 将来リターン/IC/統計サマリー等
  - monitoring/ (※将来的に監視系実装を想定)
  - strategy/ execution/ (戦略実装／発注系は別モジュール想定)

運用上の注意
-----

- OpenAI API 呼び出しは料金とレイテンシが発生します。テスト時は API 呼び出しをモックすることを推奨します（モジュール内で呼び出し関数をモック可能）。
- settings.is_live を参照して本番（実注文）と検証（ペーパー取引）を明示的に切り替えてください。
- .env ファイルの扱い:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動で読み込まれます。
  - テストや一時的に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ（テーブル作成）は ETL 実行前に環境に応じて初期化しておく必要があります（スキーマ初期化用ユーティリティは別途提供することを想定）。

トラブルシュート
-----

- 環境変数が足りない場合、Settings のプロパティが ValueError を投げます。例: JQUANTS_REFRESH_TOKEN や SLACK_BOT_TOKEN 等を確認してください。
- OpenAI の呼び出しが失敗する場合、score_news/score_regime はフォールバックやログ出力を行い得ますが、API キーの有無や制限、ネットワークを確認してください。
- J-Quants API の 401 は自動でトークンをリフレッシュするロジックがありますが、refresh token が無効だと失敗します。

ライセンス / 貢献
-----

（ここにライセンスやコントリビュートの案内を記載してください）

最後に
-----

この README はコードベースの主要な意図と使い方を概説しています。詳細は各モジュールの docstring（ファイルヘッダ）や関数のドキュメントを参照してください。必要ならば、サンプルスクリプトやスキーマ初期化スクリプトの追加も可能です。必要なものがあれば教えてください。