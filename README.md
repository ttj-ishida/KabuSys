KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
===================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買システムのコアライブラリです。本リポジトリは下記主要領域の実装を含みます。

- データ取得・ETL（J-Quants API 経由で株価・財務・市場カレンダーを取得）
- データ品質チェック・カレンダー管理・ニュース収集
- 研究用ファクター計算・特徴量探索ユーティリティ
- ニュース NLP（OpenAI を用いた銘柄センチメント算出）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- 監査ログ（シグナル→発注→約定のトレーサビリティを保証する監査DB）

主な機能
--------
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）：差分取得、保存、品質チェックを一括実行
- J-Quants クライアント（kabusys.data.jquants_client）：認証・ページネーション・リトライ・保存（DuckDB）
- ニュース収集（kabusys.data.news_collector）：RSS 収集・前処理・冪等保存
- ニュース NLP（kabusys.ai.news_nlp.score_news）：OpenAI で銘柄ごとのセンチメントを算出し ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）：ETF（1321）MA とマクロニュースを合成して daily regime を算出
- 監査ログ初期化（kabusys.data.audit.init_audit_db / init_audit_schema）：監査テーブルの作成と初期化
- 研究ユーティリティ（kabusys.research）：モメンタム・ボラティリティ・バリュー等のファクター計算と統計処理

動作環境（依存）
----------------
最低限必要な主要パッケージ（本リポジトリに requirements.txt は含まれていません。実行環境に応じてインストールしてください）：
- Python 3.10+
- duckdb
- openai（OpenAI SDK）
- defusedxml
- そのほか標準ライブラリのみで動く設計の箇所が多いですが、実稼働前にテスト・CI の依存を確認してください。

セットアップ手順
----------------
1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

3. パッケージをインストール
   - pip install -e .    （プロジェクトを編集可能モードでインストールする場合）
   - もしくは必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼出しで利用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

使い方（サンプル）
-----------------

※ 以下は最小限の利用例です。実運用前に各種トークンや DB 初期化、テーブル定義が適切に行われていることを確認してください。

1) DuckDB 接続の準備（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

# ファイルベースの DuckDB に監査スキーマを作成して接続を受け取る
audit_conn = init_audit_db(settings.duckdb_path)
# あるいは既存 conn に対して init_audit_schema(conn)
```

3) 日次 ETL 実行（株価・財務・カレンダーの差分取得・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象になります
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュースセンチメント算出（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# score_news は取得してきた記事を銘柄ごとにスコア化して ai_scores テーブルに保存します
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

5) 市場レジーム判定（ETF 1321 とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime

# OpenAI API キーを明示するか、OPENAI_API_KEY 環境変数を設定しておく
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

6) 生成されたデータや品質チェックの確認
- ai_scores / market_regime / raw_prices / raw_financials / market_calendar 等のテーブルを DuckDB で確認してください。

自動 .env ロードについて
-----------------------
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のある場所）を基に .env/.env.local を自動で読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local（上書き） > .env（未設定のみセット）
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のパースはシェル互換（export prefix / クォート / コメント等）に対応しています。

重要な設計方針（運用上の注意）
----------------------------
- ルックアヘッドバイアス防止: 各モジュールは内部で date.today() や datetime.today() を参照しない実装方針（関数に target_date を渡す）です。バックテストや再現性ある将来予測には必ず target_date を明示してください。
- OpenAI 呼び出し: API エラーはフェイルセーフ設計（多くの場合 0.0 にフォールバック）で継続するよう実装されています。ただし結果の信頼性は API レスポンスとプロンプト次第です。
- ETL は基本的に冪等（ON CONFLICT / DO UPDATE）で保存されるため再実行可能です。
- ニュース収集や外部 URL に対しては SSRF や XML Bomb 等を防ぐための対策が実装されています（defusedxml、ホスト判定、リダイレクト検査など）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- __init__.py
- config.py — 環境変数 / 設定管理（settings オブジェクトを提供）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント算出（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limiting）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の公開（再エクスポート）
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック（check_missing_data, check_spike, ...）
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

貢献方法
--------
- バグ修正・機能追加は PR をお願いします。コード変更時はユニットテストとドキュメント更新を添えてください。
- 外部 API への呼び出しや機密情報（API キー）は .env に設定し、公開リポジトリに直接コミットしないでください。

ライセンス
---------
- 本 README ではライセンスは明記していません。リポジトリルートの LICENSE ファイルを参照してください。

補足
----
- 具体的なスキーマ（テーブル定義）や API の細かいパラメータ、運用上の安全策（例: 発注時のリスク管理ルールやポジション管理）は別ドキュメント（Design/Platform ドキュメント）に準拠しています。実運用前にこれらを確認してください。

問題が発生した場合や README に追加してほしい情報があれば教えてください。必要に応じて使用例や運用手順をさらに詳しく追記します。