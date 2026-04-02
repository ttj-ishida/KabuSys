# KabuSys

日本株向け自動売買 / データプラットフォームのライブラリ群です。  
ETL（J-Quants）・ニュース収集・AIベースのニュースセンチメント評価・ファクター計算・監査ログ等のユーティリティを提供します。

主な用途:
- J-Quants API からの差分ETL（株価 / 財務 / カレンダー）
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須値チェック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込み無効化可能
- J-Quants API クライアント
  - 差分取得（ページネーション対応）／トークン管理／レートリミット／DuckDB への冪等保存
- ETL パイプライン（日次 run_daily_etl）
  - 市場カレンダー → 株価 → 財務 → 品質チェック の順で実行
  - ETL 結果を ETLResult データクラスで返却
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去／SSRF 対策／gzip 対応／raw_news への冪等保存（実装参照）
- AI モジュール（OpenAI を利用）
  - kabusys.ai.news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルに書き込み
  - kabusys.ai.regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースを組み合わせて市場レジーム判定
  - API リトライ・フォールバック設計（API失敗時は安全側のスコアで継続）
- 研究用モジュール
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）

---

## 必要環境 / 依存パッケージ（例）

- Python 3.9+
- 必須パッケージ（最低限、該当機能を使う場合）:
  - duckdb
  - openai
  - defusedxml

開発環境では次のようにインストールします（requirements.txt がある場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
requirements.txt が無い場合は最低限:
```
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

以下はコードで参照される主要な環境変数です。`.env` ファイルをリポジトリルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化されます）。

必須（本番・一部機能で必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID
- OPENAI_API_KEY : OpenAI を利用する機能（score_news / score_regime）で必要

任意（デフォルトあり）
- KABU_API_BASE_URL : kabu api のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite パス（監視 DB）（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=yourpassword
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカルでの最小構成例）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. data フォルダなど永続化先を作成
   ```
   mkdir -p data
   ```
5. プロジェクトルートに `.env` を作成し環境変数を設定
6. DuckDB ファイルを初期化する（監査ログなどを使う場合）
   Python REPL またはスクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # または既存 DuckDB 接続にスキーマを追加
   # conn = duckdb.connect("data/kabusys.duckdb")
   # from kabusys.data.audit import init_audit_schema
   # init_audit_schema(conn)
   ```

---

## 使い方（主要な例）

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作って ETL 日次パイプラインを実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアを付与（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB（独立した DB）を初期化して接続を取得
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 研究用ファクター計算の実行例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

---

## 注意点 / 運用上のポイント

- Look-ahead バイアス回避
  - 多くの関数は date.now() を内部で参照せず、明示的に target_date を渡す設計です。バックテスト等で過去の日付を使う際は target_date を明示的に渡してください。
- OpenAI / J-Quants の API はキーを要します。テストではモックして使うことを推奨します。
- .env 自動読み込みはパッケージインポート時に行われます。テスト時や明示的に環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるためコード上でチェックしています（実装に反映済み）。
- ニュース収集モジュールは SSRF / 大容量レスポンス等の対策を実装していますが、外部フィードの扱いには注意してください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他: ETL 関連モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research や data 内にさらにサブモジュールやユーティリティが含まれます。

（上記はリポジトリ内の主要モジュールを抜粋したものです。実際のファイル一覧はリポジトリを参照してください。）

---

## 開発・テスト

- 単体テスト時は OpenAI / HTTP リクエストを外部に出さないようにするため、各種ネットワーク呼び出し関数をモックしてください。コード中にもテスト用に差し替え可能な内部関数（例: _call_openai_api, _urlopen）があります。
- .env の自動読み込みを抑止するには、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はリポジトリ内のソースコード（kabusys パッケージ）に基づいて作成しています。詳しい使用方法や運用フロー（ETL スケジューリング、発注フロー等）はプロジェクトの設計ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。質問や追加のドキュメント化要望があれば教えてください。