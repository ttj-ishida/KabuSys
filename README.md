# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリ。  
DuckDB を内部データベースとして用い、J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）、品質チェック、NLP によるニューススコアリング、ファクター計算、監査ログの管理までをカバーします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／研究基盤向けユーティリティ群をモジュール化した Python パッケージです。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）
- ニュース収集（RSS）と LLM による銘柄別センチメント算出
- 市場レジーム判定（ETF + マクロニュースを組合せ）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に保存

設計上の特徴として、Look-ahead バイアス回避（日時の固定参照を避ける）、冪等性（DB への保存は ON CONFLICT で上書き）、外部 API に対する堅牢なリトライやレート制御が組み込まれています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数から設定を読み込む (.env / .env.local 自動読み込み、無効化フラグあり)
- kabusys.data
  - jquants_client: J-Quants API 呼び出し、保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: run_daily_etl など ETL パイプライン
  - quality: データ品質チェック群
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログテーブルの初期化・監査 DB ユーティリティ
  - stats: 汎用統計（zscore 正規化等）
- kabusys.ai
  - news_nlp.score_news: LLM による銘柄別ニュースセンチメント算出 → ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースで市場レジーム判定 → market_regime へ保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。
2. パッケージをインストール（ソース配布想定）
   - 開発環境や pip でのインストール方法に応じてください。例:
     ```
     pip install -e .
     ```
3. 必要な外部ライブラリ（例: duckdb, openai, defusedxml）がインストールされていることを確認してください。requirements ファイルがあればその通りにインストールします。
4. 環境変数をセットまたはプロジェクトルートに `.env` / `.env.local` を作成
   - パッケージは自動的にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client が使用）
- SLACK_BOT_TOKEN — （Slack 通知機能を使う場合）
- SLACK_CHANNEL_ID — （Slack 通知先）
- OPENAI_API_KEY — news_nlp / regime_detector 等で OpenAI を使う場合に必要

その他（デフォルト値あり）
- KABU_API_PASSWORD, KABU_API_BASE_URL
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

.env 例（プロジェクトルートに保存）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な操作例）

以下は Python REPL やスクリプトから呼ぶ簡単な例です。DuckDB 接続は kabusys.data.audit.init_audit_db / duckdb.connect を直接使います。

- DuckDB に接続（デフォルトパスを使用する例）
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # default: data/kabusys.duckdb
conn = duckdb.connect(db_path)
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026,3,19))  # 前日15:00～当日08:30(JST) の記事対象
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,19))
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026,3,19)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,19))
for i in issues:
    print(i)
```

- 監査ログ用 DB 初期化（監査専用 DB を使いたい場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# テーブルが作成され、UTC タイムゾーン設定が適用されます
```

- RSS 収集 → raw_news 保存は news_collector を組み合わせて呼び出します（fetch_rss 等）。内部で SSRF 対策・サイズ制限等が組み込まれています。

注意点
- OpenAI を使う関数は api_key 引数で明示的にキーを渡せます（テスト用）。省略時は環境変数 OPENAI_API_KEY を参照します。
- ETL / API 呼び出しは外部通信を伴います。実運用では環境変数・API キー管理・レート管理に注意してください。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys 以下を主要なパッケージとします（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング
    - regime_detector.py  — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS 収集
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログテーブル初期化 / DB ユーティリティ
    - stats.py               — 汎用統計（zscore 正規化等）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（mom/value/volatility）
    - feature_exploration.py — IC / forward returns / summary 等
  - research/
  - その他: monitoring / execution / strategy 等（パッケージヘッダでエクスポート対象あり）

---

## 開発・運用に関する補足

- 自動 .env 読み込み
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テストで自動読み込みを無効にするには環境変数を設定:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```
- レート制御・リトライ
  - J-Quants API はレート制限（120 req/min）を守るため内部に RateLimiter を持ち、HTTP エラー・ネットワークエラーに対して指数バックオフでリトライします。
- Look-ahead バイアス対策
  - 本ライブラリはバックテストや指標算出時のルックアヘッドバイアスを避けるため、関数内部で date.today() / datetime.today() を参照しない設計となっている関数が多くあります（必ず target_date を渡すことを推奨）。
- ロギング
  - 設定は環境変数 LOG_LEVEL で調整できます。運用時は INFO/DEBUG の切り替えを行ってください。

---

## よくある質問 / トラブルシューティング（Q&A）

Q: OpenAI のレスポンスで JSON パースに失敗したらどうなる？  
A: LLM 呼び出しではレスポンスのパース失敗や API エラー時にフェイルセーフとして 0.0 を返す／空辞書を返すなどの処理が組み込まれており、例外を全体に波及させない設計です（ログは出力されます）。ただし重大なエラーは呼び出し元で確認してください。

Q: DuckDB のテーブル定義はどこ？  
A: audit.init_audit_schema 等、モジュール内で DDL を定義・実行するユーティリティが提供されています。ETL 実行前にスキーマ初期化を行ってください（別モジュールに schema 初期化がある想定）。

---

## ライセンス / 貢献

この README はコードベースに基づくドキュメントです。実際のライセンス・貢献フローがリポジトリに含まれている場合はそちらを参照してください。

---

必要であれば、README に次の追記を行えます：
- データベーススキーマ（主要テーブル列）抜粋
- より具体的な運用手順（cron / ワーカー構成）
- テスト実行方法・CI 設定例

どの内容を詳述しましょうか？