# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群（KabuSys）。  
このリポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、監査ログ等を含むモジュール群を提供します。

## 概要
KabuSys は以下の目的を持った Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（rate limit・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、冪等保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロレジーム判定（JSON Mode / リトライ・フェイルセーフ）
- DuckDB を中心とした ETL パイプライン、データ品質チェック、監査ログ（発注 → 約定のトレーサビリティ）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量探索ユーティリティ

設計上の共通方針：
- ルックアヘッドバイアスを避ける（date.today() / datetime.today() を直接バックテストループ内で参照しない等）
- DuckDB へは冪等に保存（ON CONFLICT / INSERT ... DO UPDATE 等）
- 外部 API 呼び出しはリトライ・バックオフ・レートリミットなどの堅牢性を確保
- エラー時はフェイルセーフで処理継続する（重要な場面ではログ化して上位へ伝播）

---

## 主な機能一覧
- data.jquants_client: J-Quants API からのデータ取得 / DuckDB への保存（株価・財務・カレンダー、上場銘柄一覧）
- data.pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
- data.news_collector: RSS 取得 → 前処理 → raw_news への冪等保存（SSRF対策、gzip制御、ID生成）
- data.quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
- data.calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
- data.audit: 発注・約定を追跡する監査ログテーブルの初期化／操作ユーティリティ
- ai.news_nlp: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
- ai.regime_detector: ETF（1321）MA200 とマクロニュース（LLM）を組み合わせて市場レジームを判定
- research: ファクター計算（momentum, volatility, value）および特徴量解析ユーティリティ
- config: 環境変数 / .env ロード、アプリ設定ラッパー（settings）

---

## 前提条件
- Python 3.10+
- 必要なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード 等）

実際の導入では requirements.txt を用意して pip install を行ってください。最低限のインストール例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを編集可能インストールする場合:
pip install -e .
```

---

## セットアップ手順（概略）
1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
4. .env ファイルを作成して環境変数を設定（下記参照）
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. DuckDB データベースの作成（例: data/kabusys.duckdb）や監査 DB 初期化を行う

---

## 環境変数（主要）
以下はコード内で参照される主な環境変数と説明です。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）

必須変数が未設定の場合、settings プロパティ呼び出し時に ValueError が発生します。

---

## 使い方（サンプル）
以下は代表的なユースケースの呼び出し例です。Python スクリプト/REPL 内で実行してください。

- DuckDB 接続を作る（デフォルト path は settings.duckdb_path）
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む
```
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数で設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム（regime）をスコアリングして market_regime テーブルへ書き込む
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は DuckDB 接続として使用可能
```

- 研究用ファクター計算例
```
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum_records = calc_momentum(conn, date(2026,3,20))
volatility_records = calc_volatility(conn, date(2026,3,20))
value_records = calc_value(conn, date(2026,3,20))
```

注意:
- ai モジュールは OpenAI の JSON Mode を利用します。API 呼び出しはリトライやフェイルセーフを実装していますが、API キーが必要です。
- テスト目的で OpenAI 呼び出し関数（内部の _call_openai_api 等）をモック差し替えできるよう設計されています。

---

## 動作設計上の補足（重要）
- ルックアヘッドバイアス防止: 各モジュールは target_date を明示的に受け取り、date より未来のデータが使われないよう注意されています（ETL / AI スコアリング / ファクター計算等）。
- 冪等性: 差分 ETL と保存処理は基本的に冪等（ON CONFLICT / DELETE→INSERT 等）で実装されています。
- フェイルセーフ: 外部 API エラー時はゼロフォールバックやスキップで継続し、致命的な失敗はログに蓄積して呼び出し元に通知します。
- テストしやすさ: 内部の API 呼び出しはモック差替えが想定されています（ユニットテストでの注入が容易）。

---

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイルとディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - audit.py               — 監査ログ（発注／約定）テーブル初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（実運用時には data/schema 初期化や必要テーブル作成処理を行ってください。README には省略していますが、DDL は data.audit などに定義されています。）

---

## 追加のヒント / 開発者向け
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し箇所はユニットテスト時にモックしやすいよう内部関数（_call_openai_api）を経由しています。テストでは patch してレスポンスを制御してください。
- duckdb.executemany に空リストを与えると一部のバージョンでエラーになるため、コード中では空チェックをしてから executemany を呼んでいます（互換性対策）。
- J-Quants API の rate limit（120 req/min）を尊重するため固定間隔スロットリングが実装されています。

---

もし README に追加したいサンプルスクリプト、CI 設定、あるいは実際のテーブルスキーマや .env.example を含めた詳細が必要であればお知らせください。必要に応じて README を拡張します。