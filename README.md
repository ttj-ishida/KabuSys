# KabuSys

日本株向けのデータプラットフォーム／リサーチ／自動売買基盤の軽量実装コアライブラリです。  
主に以下を提供します：

- J-Quants API を使ったデータ ETL（株価、財務、JPX カレンダー）
- ニュースの収集・前処理（RSS）と LLM を使った記事センチメント評価
- 市場レジーム判定（MA200 と マクロニュースセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、監査ログ（トレーサビリティ）用の DuckDB スキーマ

設計上のポイント：
- ルックアヘッドバイアス回避（日付の扱いに注意）
- 冪等な ETL / 保存処理（ON CONFLICT 等）
- 外部 API 呼び出しに対するリトライ・バックオフ・レート制御
- セキュリティ対策（RSS の SSRF 対策等）

---

## 主な機能一覧

- Data
  - J-Quants クライアント（fetch / save / 認証、自動リフレッシュ、レート制御）
  - ETL パイプライン（run_daily_etl など）
  - カレンダー管理（市場営業日判定・更新ジョブ）
  - ニュース収集（RSS 正規化、SSRF 対策）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログスキーマ（signal / order_request / executions）

- AI
  - ニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・統計サマリーなど（feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）

- Config
  - 環境変数自動ロード（プロジェクトルートの .env / .env.local を読み込み）
  - settings オブジェクト経由の型付き設定取得

---

## 動作環境 / 依存

- Python 3.10 以上（typing に PEP 604 の `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他、標準ライブラリ（urllib, json, logging, datetime など）

（プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# パッケージが配布されている場合:
# pip install -e .
```

---

## 環境変数

自動でプロジェクトルート（.git または pyproject.toml の存在）を探し、`.env` → `.env.local` の順に読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な必須環境変数（Settings から参照される）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD
  - kabuステーション等の API パスワード（発注等に使用）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID
- OPENAI_API_KEY
  - OpenAI 呼び出し（news_nlp / regime_detector）で使用
- 任意:
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live) - デフォルト development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト INFO

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. Python 3.10+ 仮想環境を作成して有効化
2. 依存ライブラリをインストール（duckdb, openai, defusedxml 等）
3. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定
4. DuckDB ファイルの格納先ディレクトリを作成（例: data/）
5. 必要に応じて監査 DB を初期化（下記参照）

---

## 使い方（典型例）

以下は最小限の Python スクリプト例や API 呼び出し例です。すべての関数は duckdb の接続オブジェクトを受け取ります。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントスコア生成（OpenAI API 必須）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書込銘柄数
```

- 市場レジーム判定（MA200 と マクロニュースを合成）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または :memory: を指定してインメモリ DB
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュール構成は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                    （環境変数・Settings）
  - ai/
    - __init__.py
    - news_nlp.py                （ニュースの LLM スコアリング）
    - regime_detector.py         （市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py          （J-Quants API クライアント、保存関数）
    - pipeline.py                （ETL パイプライン・run_daily_etl 等）
    - etl.py                     （ETLResult エクスポート）
    - calendar_management.py     （市場カレンダー管理）
    - news_collector.py          （RSS 収集・前処理）
    - quality.py                 （データ品質チェック）
    - stats.py                   （統計ユーティリティ）
    - audit.py                   （監査ログスキーマ・初期化）
  - research/
    - __init__.py
    - factor_research.py         （モメンタム/ボラティリティ/バリュー）
    - feature_exploration.py     （将来リターン / IC / summary）
  - ai/、data/、research/ 内にさらに補助関数や内部ユーティリティが実装されています。

---

## 実装上の注意点 / 運用上の注意

- Look-ahead バイアス防止:
  - 多くの処理（news window, regime, ETL）は datetime.today() を直接用いない、また DB クエリで date 範囲の排他制御を行う設計です。バックテスト用途では特に注意してください。

- 冪等性:
  - ETL / save 関数は基本的に ON CONFLICT を用いて冪等に保存します。部分失敗時のデータ整合性に配慮した実装です。

- OpenAI 利用:
  - gpt-4o-mini を利用するプロンプト（JSON mode）で結果を厳密な JSON に期待します。API 失敗時やパース不能時はフェイルセーフ（スコア 0.0 など）で継続する実装が多くあります。

- セキュリティ:
  - RSS 取得では SSRF 対策、gzip 大きさチェック、XML の安全パース（defusedxml）等が組み込まれています。

- テスト / モック:
  - OpenAI 呼び出しやネットワーク周りはテスト時にモック差替えしやすいよう設計されています（内部呼び出し関数を patch する想定）。

---

## 開発・拡張

- 新しい ETL 対象や保存先を追加する場合は `kabusys.data.jquants_client` の fetch / save インターフェースに合わせて実装するとパイプラインに組み込みやすいです。
- AI プロンプトやモデルを切り替える際は `ai/*.py` 内のモデル定数とプロンプトを更新してください。
- 監査（audit）スキーマは冪等で初期化できます。運用開始時に一度 `init_audit_db` を実行してください。

---

必要に応じて README にサンプルの .env.example や requirements.txt、簡単な CLI スクリプト（etl_runner.py 等）を追記できます。追記希望があれば実行例やテンプレートを作成します。