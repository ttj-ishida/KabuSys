# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース収集・LLM を使ったニュース/マクロ判定・リサーチ（ファクター）・監査ログ等、運用に必要なユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・戦略検証・発注監査までを支える内部ライブラリのセットです。主な設計方針は以下です。

- Look-ahead bias を避ける（コード内で datetime.today() を直接参照しない等の実装）
- DuckDB を中心としたローカルデータベース保存（冪等な INSERT / ON CONFLICT ロジック）
- API 呼び出しに対する堅牢なリトライ・レート制御・トークンリフレッシュ
- ニュース収集に対する SSRF 対策・サイズ制限・XML パース保護
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・マクロ判定機能（JSON モード使用）
- 監査ログテーブル（signal → order_request → executions）の初期化ユーティリティ

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み、必須値チェック、環境種別判定（development / paper_trading / live）
- データ ETL（kabusys.data.pipeline, jquants_client 等）
  - J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB 保存（冪等）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - カレンダー管理（営業日判定、次/前営業日取得）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news / news_symbols への保存。SSRF 防止・Gzip・サイズチェック
- AI 支援（kabusys.ai）
  - ニュースセンチメント分析（score_news）：銘柄ごとに LLM でスコア化して ai_scores に保存
  - 市場レジーム判定（score_regime）：ETF(1321) の MA とマクロニュースの LLM 評価の合成
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計測、IC 計算、統計サマリー、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の DDL 定義と初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（typing の新構文を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクトに合わせて requirements.txt を用意してください。

---

## 環境変数 (.env)

自動でプロジェクトルート（.git または pyproject.toml の有無で判定）から `.env` と `.env.local` を読み込みます。  
自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）

任意 / デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値があれば無効）

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # テストや開発ツールがあれば追加でインストール
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成し上記の必須値を設定します。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定。

5. DuckDB データベースを作成（任意）
   - ETL 実行前にデータベースを作成しておくと便利です。以下は簡単な例：
   ```py
   import duckdb
   conn = duckdb.connect('data/kabusys.duckdb')
   # 必要な初期スキーマを適宜作成してください（schema 初期化関数があれば使用）
   conn.close()
   ```

---

## 使い方（簡単な例）

以下は各主要 API の利用例（Python REPL やスクリプトで実行）。

1) ETL を実行（J-Quants からの差分取り込み）
```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores テーブルに書き込む
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書込銘柄数: {written}")
```

3) 市場レジーム（bull/neutral/bear）を判定して market_regime に保存
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 03, 20), api_key=None)
```

4) 監査ログ用 DB 初期化
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# conn は作成済みの DuckDB 接続を返す
```

5) ファクター計算 / リサーチ
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意:
- score_news / score_regime は OpenAI API 呼び出しを伴います。API キーが必要です。
- 多くの関数は DuckDB に必要なテーブル（raw_prices, raw_financials, raw_news, news_symbols, prices_daily 等）が存在することを前提としています。ETL によってこれらを作成・充填してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソースは `src/kabusys` 以下に格納されています。主なモジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（LLM）
  - regime_detector.py  — 市場レジーム判定（MA + マクロニュース）
- src/kabusys/data/
  - __init__.py
  - pipeline.py         — ETL パイプライン実装、run_daily_etl 等
  - jquants_client.py   — J-Quants API クライアント & DuckDB 保存関数
  - news_collector.py   — RSS 収集・正規化・保存
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize 等）
  - audit.py            — 監査ログ（DDL / 初期化）
  - etl.py              — ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外にも strategy/execution/monitoring 等のサブパッケージが意図されており、将来的な拡張点があります）。

---

## 設計上の注意点 / 安全機構

- Look-ahead bias を避けるため、target_date を引数で受け取る設計が基本です。内部で現在日時を直接参照する実装を避けています。
- J-Quants クライアントはレート制限（120 req/min）を守る仕組みと、401 に対する自動トークンリフレッシュを備えています。
- ニュース収集は SSRF を考慮した検証（リダイレクト先チェック、プライベート IP 検査）や XML の安全処理（defusedxml）を行います。
- OpenAI 呼び出しはリトライやパース失敗時のフォールバックを備えており、API エラーでプロセス全体が停止しない設計になっています（失敗時は 0.0 等で継続）。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で行われるため、再実行に強い構造です。

---

## よくある質問 / トラブルシューティング

- 自動的に .env がロードされない
  - プロジェクトルートが .git または pyproject.toml によって検出されます。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- OpenAI のレスポンスが JSON 以外を返す
  - モジュール側で可能な限り JSON を抽出しパースしますが、異常時はスコアを 0.0 にフォールバックします。ログを参照して原因を特定してください。
- DuckDB に必要なテーブルがない
  - ETL（run_daily_etl）やスキーマ初期化関数（audit.init_audit_db 等）を実行してテーブルを準備してください。

---

## 貢献 / 拡張

- strategy / execution / monitoring などの実際の発注ロジックや監視ダッシュボードの実装を追加して、フルスタック自動売買システムに拡張できます。
- ETL のテストケース、モック J-Quants / OpenAI クライアントを整備するとユニットテストが書きやすくなります。

---

必要であれば README に入れてほしい追加情報（例: CLI コマンド、詳細なスキーマ一覧、サンプル .env.example）を教えてください。