# KabuSys

日本株向けのデータプラットフォーム／自動売買支援ライブラリです。  
J-Quants / kabuステーション / OpenAI 等を組み合わせ、データ収集（ETL）、品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログの管理などを提供します。

---

## プロジェクト概要

KabuSys は以下を主目的とした内部ライブラリ群です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース（RSS）収集と記事の前処理／銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄単位）およびマクロセンチメント解析
- ETF とマクロセンチメントを統合した市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）と特徴量探索（IC / forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定までの監査ログ（DuckDB）初期化・管理

設計上の特徴として、ルックアヘッドバイアスを避けるために内部で安易に `date.today()`／`datetime.today()` を参照しない実装方針が各所で採られています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン管理、レートリミット、リトライ）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、トラッキング除去）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（missing / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（銘柄単位のセンチメント算出: score_news）
  - 市場レジーム判定（ETF MA200 乖離 + マクロセンチメントの合成: score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns / IC / factor summary / rank）
- config
  - 環境変数管理（.env 自動読み込み、必須設定の検査）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の `X | Y` 型ヒントを使用）
- DuckDB を利用（ローカル DB ファイルに保存）
- OpenAI API、J-Quants トークン、kabu API パスワード等の外部キーが必要

1. リポジトリをクローン／インストール
   - 開発環境ではソースを editable インストールするのが便利です:
     - pip install -e .

2. 必要なパッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （その他標準ライブラリのみで多く実装されています）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主に必要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用する場合）
   - SLACK_CHANNEL_ID (必須) — Slack 投稿先チャンネル ID（使用する場合）
   - OPENAI_API_KEY (任意引数で上書き可能) — OpenAI 呼び出しに使用

   データベースパス（デフォルト値、必要に応じて上書き）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db

4. DB 初期化（任意）
   - 監査ログ用 DB の初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 他のスキーマ初期化については、呼び出す側で該当 DDL を用意してください（audit モジュールは監査テーブルを作成します）。

---

## 使い方（簡単なコード例）

※ いくつかの操作は外部 API（J-Quants / OpenAI）を呼び出します。事前に環境変数か引数で API キーをセットしてください。

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path オブジェクト
print(settings.env)           # development | paper_trading | live
```

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア生成（銘柄別）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-....")  # api_key を省略すると env の OPENAI_API_KEY を使用
print(f"wrote {n_written} ai_scores")
```

- マーケットレジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用関数（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマの初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須：Slack 通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須：Slack 通知を使う場合）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動で .env を読み込まない

自動読み込みの優先順位:
- OS 環境変数 > .env.local > .env
- プロジェクトルートの探索は .git または pyproject.toml を基準に行われ、見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定読み込み・検証
- ai/
  - __init__.py
  - news_nlp.py                   — 銘柄別ニュース NLP（score_news）
  - regime_detector.py            — ETF MA とマクロセンチメント合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETL インターフェース再エクスポート（ETLResult）
  - news_collector.py             — RSS 収集・前処理・SSRF 対策
  - calendar_management.py        — 市場カレンダー（営業日判定 / update job）
  - quality.py                    — データ品質チェック（各種チェック）
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
  - audit.py                      — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py            — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py        — forward returns / calc_ic / factor_summary / rank

その他：
- README.md（本ファイル）
- .env.example（想定される .env のテンプレート — プロジェクトルートに置く想定）

---

## 注意事項 / 運用上のポイント

- OpenAI や J-Quants を呼ぶ関数はネットワーク I/O / 認証を伴います。API キーの管理とレート制限に注意してください。
- ETL 系は差分更新・バックフィルロジックを持ちますが、初回ロード時は開始日（_MIN_DATA_DATE）から大量データを取得します。テスト時は範囲を狭く指定してください。
- DuckDB の executemany と空リストの挙動、バージョン差異を一部コードで考慮しています（例: DuckDB 0.10 の制約）。
- ニュース収集では SSRF 対策・XML パース防御（defusedxml）・サイズ制限を実装しています。外部 RSS の扱いは慎重に行ってください。
- 監査ログテーブルは削除を想定していない運用（FOREIGN KEY ON DELETE RESTRICT）です。スキーマの変更は慎重に行ってください。

---

問題や追加の用途（例：backtest 用のデータエクスポート・運用スケジュールの例）について詳しくドキュメント化が必要であれば、目的に合わせた使用例や運用手順を追記します。必要な箇所を教えてください。