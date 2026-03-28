KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
---
KabuSys は日本株のデータ収集（ETL）・品質チェック・ファクター計算・ニュース NLP（LLM）・市場レジーム判定・監査ログ管理を備えたバックオフィス／リサーチ向け共通ライブラリです。  
主に DuckDB をデータ層に用い、J-Quants API、RSS ニュース、OpenAI（gpt-4o-mini など）を組み合わせて自動化パイプラインを構築します。

主な特徴
---
- データ ETL（株価日足 / 財務 / 市場カレンダー） — 差分取得・ページネーション対応・冪等保存
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理、銘柄紐付け、NLP による銘柄別センチメント計算（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン・IC・統計サマリー）
- 監査ログ（signal → order_request → execution のトレース可能なテーブル設計）
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ込み）
- 環境変数管理（プロジェクトルートの .env / .env.local を自動読み込み。無効化フラグあり）

必須 / 推奨環境
---
- Python 3.10 以上（PEP 604 の型注釈 `X | None` を使用しているため）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- 標準ライブラリの urllib, gzip, logging 等

主な環境変数
---
（README に書かれている各設定は kabusys.config.Settings で参照されます）
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime のデフォルト）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" に設定すると .env 自動読み込みを無効化

セットアップ手順
---
1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .                 # setup.py / pyproject.toml がある想定
   - 必要パッケージの例:
     - duckdb
     - openai
     - defusedxml

4. .env を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動的に読み込まれます（.env.local は .env の上書き）。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースの準備
   - DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。初期化用の SQL を実行するユーティリティが別途ある想定です（例: data.schema.init_schema() 相当）。

簡単な使い方（コード例）
---
下記はライブラリの主要 API を呼ぶときの例です。実行前に必要な環境変数を設定してください。

- 日次 ETL を実行（J-Quants から株価・財務・カレンダーを取得／保存／品質チェック）
```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）をスコアリング
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログテーブル初期化（監査専用 DB を別に作る場合）
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn に対して監査ログを書き込める
```

主なモジュールと用途
---
- kabusys.config — .env / 環境変数読み込み、Settings オブジェクト
- kabusys.data.jquants_client — J-Quants API クライアント（取得・保存ユーティリティ）
- kabusys.data.pipeline — ETL パイプライン（run_daily_etl 等）
- kabusys.data.quality — 品質チェック（欠損 / スパイク / 重複 / 日付整合性）
- kabusys.data.news_collector — RSS 収集・前処理
- kabusys.data.audit — 監査ログスキーマ初期化
- kabusys.ai.news_nlp — ニュースを LLM でスコアリング（score_news）
- kabusys.ai.regime_detector — 市場レジーム判定（score_regime）
- kabusys.research — ファクター計算・特徴量解析ユーティリティ

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                         — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP スコアリング（score_news）
  - regime_detector.py               — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント + 保存関数
  - pipeline.py                      — ETL パイプライン（run_daily_etl など）
  - etl.py                           — ETLResult 再エクスポート
  - news_collector.py                — RSS 収集・前処理
  - quality.py                       — データ品質チェック
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py           — 市場カレンダー管理（営業日判定等）
  - audit.py                         — 監査ログ初期化（テーブル・インデックス）
- research/
  - __init__.py
  - factor_research.py               — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py           — 将来リターン・IC・統計サマリー

設計上の注意点 / ポリシー
---
- Look-ahead bias（ルックアヘッド）対策が至る箇所で考慮されています：
  - target_date 引数ベースで処理し、datetime.today() を内部ロジックで直接参照しない関数設計
  - データ取得時の fetched_at を記録して「いつそのデータが入手可能だったか」をトレース可能にする
- 外部 API 呼び出しはリトライと指数バックオフ、エラー時のフェイルセーフ（部分的失敗を許容）を備えています
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています
- RSS パーサーは defusedxml / SSRF 対策 / レスポンスサイズ制限 等、安全性に配慮

よくある質問（FAQ）
---
Q: .env を自動で読み込ませたくない場合は？
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。そうすると config の自動ロードをスキップします。

Q: OpenAI API キーをどのように渡すべきですか？
A: score_news / score_regime の api_key 引数に明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。

Q: DuckDB の初期スキーマはどこで作成しますか？
A: ここに載せたコードには全スキーマ初期化の単一エントリポイントが明示されていませんが、監査ログは data.audit.init_audit_db / init_audit_schema で初期化できます。その他スキーマはプロジェクトの schema 初期化スクリプトから作成してください（ETL が INSERT するテーブルが必要です）。

貢献 / テスト
---
- コントリビューションや Issue、PR は歓迎します。ユニットテストはモジュール毎に mock を使って外部依存を切り離して実装することを推奨します（例: OpenAI 呼び出し・HTTP リクエスト・DuckDB 接続など）。
- 自動テストや CI の設定はプロジェクト側で追加してください。

ライセンス
---
プロジェクトのライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（ここでは言及のみ）。

最後に
---
この README はコードベース（src/kabusys）をもとに要点をまとめたものです。各モジュールにはさらに詳細な docstring と設計方針コメントが含まれていますので、実装や拡張時は該当モジュールの docstring を参照してください。質問があればどうぞ。