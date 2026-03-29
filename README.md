KabuSys — 日本株自動売買／データプラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI（ニュースNLP）、
および監査ログを含む自動売買プラットフォームのコアライブラリ群です。
主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント算出
- マーケットレジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定の追跡）
- 再利用しやすいモジュール設計（DuckDB 接続を受け取る関数群、フェイルセーフ設計）

主な機能一覧
--------------
- data.jquants_client: J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
- data.pipeline: 日次 ETL のエントリポイント（run_daily_etl）と個別 ETL（prices/financials/calendar）
- data.news_collector: RSS からのニュース収集と raw_news への安全な保存（SSRF 対策等）
- data.quality: raw_prices 等に対する品質チェック（欠損・スパイク・重複・日付不整合）
- data.calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
- data.audit: 監査ログ（signal_events / order_requests / executions）のスキーマ作成・初期化
- data.etl, data.stats: ETL ヘルパーと統計ユーティリティ（zscore_normalize 等）
- ai.news_nlp: ニュースを LLM（OpenAI）で評価して ai_scores テーブルへ書き込み
- ai.regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジームを判定
- research.*: ファクター計算（momentum/value/volatility）と特徴量探索（forward returns, IC, summary）

設計上のポイント（抜粋）
- Look-ahead バイアス防止: 内部で datetime.today()/date.today() を直接参照しない設計
- フェイルセーフ: API 呼び出し失敗時はロギングして安全なデフォルトで継続（例: macro_sentiment=0）
- 冪等性: DB への保存は ON CONFLICT / DELETE→INSERT といった冪等操作で実装
- セキュリティ: RSS 取得での SSRF 対策、defusedxml の利用、レスポンスサイズ制限 等

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union | を利用）
- ネットワーク接続（J-Quants / OpenAI / RSS）
- 推奨パッケージ: duckdb, openai, defusedxml

1. レポジトリを取得
   - git clone <repo-url>
   - またはソースを配置

2. 仮想環境作成と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   # requirements.txt があれば:
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定 (.env)
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動読み込みされます。
   自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（data.jquants_client で使用）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合（必須としている部分あり）
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード

   任意 / デフォルトあり
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると自動 .env ロードを無効化
   - OPENAI_API_KEY: OpenAI を使う関数に必要（関数呼び出し時に引数で渡すことも可能）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用など）（デフォルト data/monitoring.db）

4. DB 初期化（監査用 DB 例）
   以下は監査ログ用の DuckDB を初期化する例です（path は適宜調整）。
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   run_daily_etl 等を使う場合は settings.duckdb_path を参照して接続を作るのが便利です。

使い方（コード例）
-------------------

基本的に各関数は DuckDB 接続（duckdb.connect() の戻り値）を受け取ります。

1) 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores 生成）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数で設定済みなら api_key=None で良い
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

3) 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマ初期化（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)
```

5) J-Quants の id_token を手動で取得（テスト等）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

実行時の注意点
- OpenAI の呼び出しは API キー（OPENAI_API_KEY）が必要です。score_news / score_regime は引数で api_key を明示的に渡すこともできます。
- J-Quants API はレート制限（120 req/min）に従って実装済みですが、ETL 実行時はネットワーク状況や API レートに注意してください。
- ETL / AI 呼び出しは外部 API に依存します。失敗時はログが残り安全なフォールバック（例: スコア 0）を取る設計です。
- DuckDB は executemany の空リストに制約があるバージョンがあるため、コード内で空チェックを行っています。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py               — パッケージ初期化（バージョン情報等）
- config.py                 — 環境変数／設定管理（.env 自動読み込みロジック含む）

src/kabusys/ai/
- __init__.py               — ai パッケージ公開（score_news）
- news_nlp.py               — ニュースセンチメントスコアリング（OpenAI 経由）
- regime_detector.py        — 市場レジーム判定ロジック（ETF MA + マクロニュース）

src/kabusys/data/
- __init__.py
- jquants_client.py         — J-Quants API クライアント（取得 / 保存 / 認証 / リトライ）
- pipeline.py               — ETL パイプライン（run_daily_etl など）
- etl.py                    — ETLResult の再エクスポート
- news_collector.py         — RSS 収集 / raw_news 保存（SSRF 対策・正規化）
- quality.py                — データ品質チェック（欠損・スパイク・重複・日付不整合）
- calendar_management.py    — マーケットカレンダー管理・営業日計算
- stats.py                  — 統計ユーティリティ（zscore_normalize）
- audit.py                  — 監査ログ（テーブル DDL / 初期化 / init_audit_db）

src/kabusys/research/
- __init__.py
- factor_research.py        — ファクター計算（momentum/value/volatility）
- feature_exploration.py    — 将来リターン / IC / 統計サマリー等

（その他）
- strategy/, execution/, monitoring/ 等の上位モジュールは __all__ に名前が挙がる箇所がありますが、
  実際のサブパッケージはこのスニペット内に含まれていない可能性があります。実環境ではプロジェクト全体のツリーを参照してください。

開発・テスト
------------
- 自動 .env 読み込みはデフォルト有効。ユニットテスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の外部 API 呼び出し部分はモック可能な設計になっています（テストで差し替え可能）。
- DuckDB を用いた単体テストはインメモリ ":memory:" を使うと便利です（init_audit_db(":memory:") 等）。

ライセンス・貢献
----------------
（ここにはプロジェクトのライセンス表記や貢献ガイドを入れてください。リポジトリに合わせて追記してください。）

補足
----
- 詳細な仕様（DataPlatform.md / StrategyModel.md など）に基づいた実装が多く含まれます。設計判断や注意点は各モジュールの docstring に記載されていますので、実装を変更する場合はそちらも参照してください。
- 本 README はコードスニペットから自動生成した概要です。導入や運用の際は実際のリポジトリに含まれるドキュメント・example を優先してください。

必要であれば、README に含める実行コマンド例や .env.example のテンプレート、よくあるトラブルシューティング（例: OpenAI レスポンスパース失敗時の対処）を追加します。要望があれば教えてください。