# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログ（約定トレーサビリティ）など、トレーディング運用に必要な機能をモジュール化して提供します。

---

## 主な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API から株価日足（OHLCV）、財務情報、JPX マーケットカレンダーを差分取得・保存
  - DuckDB へ冪等（ON CONFLICT）で保存
  - 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集・前処理
  - RSS フィード取得 + URL 正規化（トラッキング除去） + テキスト前処理
  - SSRF / Gzip bomb 等への防御機能を備えた実装

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM へ送りセンチメント（ai_scores）を計算
  - マクロニュースを LLM で評価して市場レジーム（bull/neutral/bear）を判定

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリー、Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events, order_requests, executions といった監査テーブルのスキーマ初期化とユーティリティ
  - UUID ベースのトレーサビリティ、冪等性・ステータス管理

- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み（自動ロード。無効化可）

---

## 要件（主要ライブラリ）

- Python 3.10+
- duckdb
- openai（OpenAI の Python SDK）
- defusedxml
- 標準ライブラリのみで動く部分も多く設計されていますが、実運用では上記が必要になります。

（実際のバージョンはプロジェクト配布時の pyproject.toml / requirements を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
   - 例: git clone ...

2. 仮想環境を作成して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -e .  または pip install -r requirements.txt

3. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` と `.env.local` を置けます。
   - 自動ロードはデフォルトで有効。テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（利用する機能に応じて設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しが必要な機能を使う場合（score_news / score_regime 等）

設定の読み込みと検証は `kabusys.config.settings` を通して行います。デフォルトの DB パスは次の通りです:
- DuckDB: data/kabusys.duckdb（settings.duckdb_path）
- SQLite（monitoring）: data/monitoring.db（settings.sqlite_path）

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの利用例です。各例では DuckDB 接続オブジェクト (`duckdb.connect(...)`) を受け渡して使用します。

- ETL（日次）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- J-Quants からデータ取得（単体）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token は get_id_token() が settings.jquants_refresh_token を使用して返します
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

- ニュースセンチメント（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print("書込み件数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（監査DB作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。init_audit_db はテーブル／インデックスを作成します。
```

- 研究モジュール（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabuステーション API のパスワード（Settings.kabu_api_password）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（Settings.duckdb_path、省略時 data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（Settings.sqlite_path）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

ヒント:
- .env / .env.local はプロジェクトルートから自動読込されます（優先度: OS環境 > .env.local > .env）。
- 自動読込を無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 注意・設計方針の要点

- Look-ahead bias を避けるため、各モジュールは内部で datetime.today() や date.today() を不用意に参照しない設計になっています。API 呼び出し時やスコア計算は対象日を明示して行うことを想定しています。
- API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ、フェイルセーフ（失敗時にゼロやスキップして継続）を取り入れています。運用者側で失敗時の扱いをログや通知で監視してください。
- DuckDB に対する一連の保存処理は冪等（ON CONFLICT）で設計されていますが、ETL やマイグレーションの手順は運用ポリシーに合わせて実行してください。

---

## ディレクトリ構成（主要ファイル / モジュール）

プロジェクトは `src/kabusys` 配下にモジュールを配置しています。重要なファイル・サブパッケージを抜粋します。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス
- src/kabusys/ai/
  - news_nlp.py        : ニュースの LLM によるセンチメント付与（score_news）
  - regime_detector.py : マクロセンチメント + ETF MA で市場レジーム判定（score_regime）
- src/kabusys/data/
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - jquants_client.py      : J-Quants API クライアント（fetch/save 系）
  - news_collector.py      : RSS 取得 / 前処理 / 保存
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - quality.py             : データ品質チェック
  - stats.py               : zscore_normalize 等の統計ユーティリティ
  - audit.py               : 監査ログスキーマの初期化
  - etl.py                 : ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py     : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py : 将来リターン / IC / rank / summary 等
- src/kabusys/ai/__init__.py
- src/kabusys/research/__init__.py
- その他ユーティリティやサブモジュール群

（上記は要点の抜粋です。詳細はソースコードを参照してください。）

---

## 開発・運用上のヒント

- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動 .env 読み込みを止め、必要な環境変数を明示的にセットしてください。
- OpenAI 呼び出しはテストでモック可能なように内部関数が分離されています（ユニットテスト時はモックを推奨）。
- DuckDB のバージョン差（executemany の挙動など）に配慮して一部ガードロジックが入っています。運用環境での duckdb バージョンは固定することを推奨します。

---

README の内容についてさらに詳しい例（実行スクリプト、CI、運用手順）や .env.example のテンプレートが必要であれば、利用シナリオに合わせて追記します。必要な箇所を教えてください。