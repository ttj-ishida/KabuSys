# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買基盤のコアライブラリです。  
J-Quants / RSS / OpenAI（LLM）などからのデータ取得、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）といった機能群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date/datetime を明示的に渡す）
- DuckDB を主要なデータ格納先として利用
- 冪等性・トランザクションを重視した保存処理
- 外部 API 呼び出しに対する堅牢なリトライ / フェイルセーフ実装

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）・財務データ・上場情報・マーケットカレンダーを差分取得・保存
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを自動化
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比閾値）、重複、日付整合性チェック
- ニュース収集 / NLP
  - RSS からの記事取得（SSRF 対策・サイズ制限・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア生成（score_news）
- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull / neutral / bear）（score_regime）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによるシグナル→注文→約定の完全トレーサビリティ
  - 監査用 DuckDB 初期化ユーティリティ（init_audit_db）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

---

## 必要な環境変数（設定）

以下は動作に必要または利用される主な環境変数です（.env に記述して管理する想定）。

必須（実行する機能によっては一部のみ必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行時の注文連携など）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロードについて:
- パッケージ初期化時にプロジェクトルート（.git or pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- 自動ロードは OS 環境変数を保護（上書き防止）するロジックを備えています。

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <this-repo>

2. Python 環境（推奨）
   - Python 3.10 以降を推奨（duckdb / openai ライブラリと互換のあるバージョンを使用してください）
   - 仮想環境作成推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限のパッケージ例:
     - pip install duckdb openai defusedxml
   - パッケージ管理ファイル（requirements.txt / pyproject.toml）がある場合はそちらを利用してください。
   - 開発時は linters / test ライブラリを追加でインストールして下さい。

4. 環境変数の設定
   - プロジェクトルートに `.env` を作り、上記の必須変数を設定します。
   - 自動読み込みを無効にしたいユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DuckDB の準備
   - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb。存在しない場合は自動作成されますが、権限に注意してください。

---

## 使い方（簡単な例）

以下は主要ユーティリティの利用例です。いずれも Python スクリプトや REPL から呼び出せます。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア（銘柄ごと）を生成する（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

3) 市場レジーム判定を実行する
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査用 DuckDB を初期化する（order/execution などのテーブルを作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# conn は初期化済み DuckDB 接続
```

5) 研究用関数の利用例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

注意点:
- LLM を使う機能（score_news, score_regime）は OpenAI API の課金対象です。APIキーの管理に注意してください。
- run_daily_etl は内部で J-Quants API を呼びます。J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）が必要です。
- すべてのユーティリティは「与えられた target_date を基準に処理」する設計になっており、内部で date.today() を参照してルックアヘッドバイアスを生まないよう工夫されています。バッチやテストで任意の日付を渡して使ってください。

---

## 主要モジュール・ディレクトリ構成

概略ツリー（src/kabusys）:

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py
    - 環境変数の自動ロード・設定取得ロジック（settings）
  - ai/
    - __init__.py
    - news_nlp.py       : ニュース NLP（OpenAI 呼び出し、score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - etl.py               : ETL 関連の公開型（ETLResult）
    - quality.py           : データ品質チェック
    - stats.py             : 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py: マーケットカレンダー管理（営業日判定等）
    - news_collector.py    : RSS ニュース収集（SSRF 対策等）
    - audit.py             : 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py   : ファクター計算（momentum/value/volatility）
    - feature_exploration.py: 将来リターン、IC、統計サマリー等
  - ai、data、research 各モジュールは DuckDB 接続を受け取り副作用を最小化する設計です。

---

## 開発・テスト時のメモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。CI などで制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして下さい。
- OpenAI 呼び出しや外部 HTTP の振る舞いはテストしやすいように内部の呼び出し関数（_call_openai_api, _urlopen など）をモックできるよう設計されています。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性考慮があります（コード中で空チェックを行っています）。

---

## 参考・追加情報

- OpenAI のモデルは現状 gpt-4o-mini を使用するよう設定されています（news/regime モジュール内の _MODEL 定数）。
- J-Quants API 呼び出しはレート制御、401 自動リフレッシュ、指数バックオフ等の堅牢化が施されています。
- 本 README はコードベースの現状に基づいて作成しました。外部 API 仕様や依存ライブラリの更新に伴い、環境変数や挙動が変わる可能性があります。

---

問題や追加で README に載せたい情報（例: CI、ライセンス、詳細な .env.example）などがあれば教えてください。必要に応じて README を拡張します。