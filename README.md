# KabuSys — 日本株自動売買基盤（README）

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買の基盤ライブラリです。  
J-Quants API からのデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（注文／約定トレーサビリティ）などを含みます。パッケージは src/kabusys 以下に分割され、DuckDB を主要な保存先として想定しています。

主な特徴
--------
- データ ETL（株価日足・財務・市場カレンダー）/ 差分更新
- ニュース収集（RSS）・前処理・銘柄紐付け
- OpenAI を用いたニュースセンチメント分析（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の 200 日 MA とマクロセンチメントの合成）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）および探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブルの自動初期化（signal_events / order_requests / executions）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
- DuckDB による冪等な保存（ON CONFLICT / executemany の考慮）

動作要件（推奨）
----------------
- Python 3.10+
- パッケージ: duckdb, openai, defusedxml（その他標準ライブラリ）
- J-Quants API と OpenAI API の利用には各種 API キーが必要

インストール（開発環境）
---------------------
仮想環境を作成してパッケージをインストールします（プロジェクトルートが pyproject.toml を持つ場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# ローカル開発用にパッケージ化している場合
pip install -e .
```

環境変数（.env）
----------------
プロジェクトはルートの .env / .env.local を自動ロードします（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必要環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順（簡易）
---------------------
1. Python 仮想環境作成・依存インストール（上記参照）
2. .env（または環境変数）を配置・設定
3. DuckDB スキーマ作成（必要に応じて schema 初期化スクリプトを実行）
   - 監査ログ用 DB 初期化例（スクリプトや REPL で実行）:

```python
import duckdb
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を保持して監査ログに利用できます
```

基本的な使い方
-------------
（すべて duckdb 接続を渡して呼び出す設計です。関数はルックアヘッドバイアスを避けるため内部で date.today() を直接参照しないよう注意して実装されています。）

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を作成する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使うなら api_key=None
print("scored:", n_written)
```

- 市場レジームスコアを算出する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（研究用途）:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- データ品質チェックを走らせる:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

実装上の注意点
--------------
- 多くの関数は外部 API（J-Quants / OpenAI）を呼びます。API 呼び出しは課金やレート制限があるため、設定やリトライの挙動に注意してください。
- OpenAI 呼び出しでは JSON Mode を活用し、レスポンス検証・フォールバック（失敗時はゼロ等の安全値）を行っていますが、運用でのモニタリングを推奨します。
- ETL/品質チェックは一部の例外を捕捉して処理を継続する設計です。重大な品質問題（QualityIssue.severity == "error"）は run_daily_etl の戻り値で確認できます。
- DuckDB に対する executemany の空リスト処理など、互換性に配慮した実装が含まれています。

ディレクトリ構成（主なファイル）
------------------------------
プロジェクトの主要なモジュール構成（抜粋）:

src/kabusys/
- __init__.py
- config.py                         — 環境変数/設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP（OpenAI）
  - regime_detector.py               — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETL インターフェース（ETLResult）
  - news_collector.py                — RSS 収集・前処理
  - calendar_management.py           — マーケットカレンダー管理
  - quality.py                       — データ品質チェック
  - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                         — 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py               — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py           — 将来リターン/IC/統計サマリ
- research/...（補助モジュール）
- その他: strategy/, execution/, monitoring/（__all__ に含まれるが別ファイル群）

運用・開発時の Tips
-------------------
- 自動読み込みされる .env / .env.local の優先度: OS 環境 > .env.local > .env。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しはモジュール内で _call_openai_api を経由しているため、ユニットテストではこの関数をモックして外部依存を切り離せます。
- news_collector は SSRF 対策・受信サイズ上限・XML デフューズ化を行っていますが、運用でのソース追加時は信頼できるフィードのみを追加してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb。複数環境（ローカル/本番）を分けたい場合は DUCKDB_PATH を変更してください。

ライセンス／貢献
----------------
本リポジトリのライセンス情報やコントリビュート方針はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本 README は実装ベースの簡易ドキュメントです）。

さらに知りたい点や、サンプルスクリプト（cron 用実行例、CI での ETL テスト、監査 DB マイグレーション等）が必要であれば教えてください。README を追加の手順やスクリプト例で拡張します。