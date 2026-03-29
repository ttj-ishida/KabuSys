# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー/約定のトレーサビリティ）などを提供します。

主な目的は「データ取得→品質管理→リサーチ→シグナル生成→発注監査」を一貫してサポートする基盤ライブラリです。

---

## 主要な機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  - 上場銘柄一覧
  - ページネーション、レートリミット、トークン自動リフレッシュ、冪等保存
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を ETLResult として返却
- データ品質チェック
  - check_missing_data / check_duplicates / check_spike / check_date_consistency
  - run_all_checks
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants からのカレンダー差分取得）
- ニュース収集
  - RSS 取得（SSRF対策、サイズ制限、URL 正規化、記事ID生成）
  - raw_news / news_symbols との連携を想定
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとのセンチメント（ai_scores テーブルへ書き込み）
  - バッチ分割、トリム、レスポンス検証、リトライ
- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
  - score_regime: ma200 と LLM（OpenAI）によるマクロセンチメントを合成して regime を保存
- 研究系ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算 / IC 計算 / 統計サマリー / zscore 正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - init_audit_schema / init_audit_db（冪等にテーブルを作成）
- 共通ユーティリティ
  - 環境設定 / .env 自動ロード（kabusys.config）
  - 統計ユーティリティ（zscore_normalize）

---

## 環境変数（主要なもの）

kabusys は .env ファイルまたは OS 環境変数から設定を読み込みます（自動ロード機能あり）。以下は主な環境変数：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env の読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

備考: settings オブジェクトからこれらにアクセスできます。
例:
from kabusys.config import settings
token = settings.jquants_refresh_token

---

## セットアップ（開発環境向け）

以下は一般的なセットアップ手順です。プロジェクト配布時のパッケージ管理に依存しますが、最低限必要となるライブラリは README に列挙したものです。

1. Python 3.10+ をインストール（typing の型ヒントを活用しています）。
2. リポジトリをクローンして仮想環境を作成・有効化。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）:
   - pip install duckdb openai defusedxml
   - （必要に応じて logging, urllib は標準ライブラリ）
   - 実運用では requirements.txt / pyproject.toml に依存を追加してください。
4. パッケージをインストール（プロジェクトルートで）:
   - pip install -e .
   （または適切なビルド手順）
5. .env を作成（.env.example がある場合はそれを参照）。少なくとも JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD は設定してください。

---

## 使い方（例）

- DuckDB 接続と ETL 実行（日次 ETL）:

```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクトを返す
conn = duckdb.connect(str("data/kabusys.duckdb"))  # 例: settings.duckdb_path を使用
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（ただし内部で営業日に調整）
print(result.to_dict())
```

- ニュースの NLP スコア（OpenAI キーを引数で渡すか OPENAI_API_KEY を環境変数で指定）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。必要に応じて transactional=True オプションの init_audit_schema を使用。
```

- 設定取得の例:

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path("data/kabusys.duckdb")
print(settings.env, settings.log_level)
```

注意:
- score_news / score_regime は OpenAI の Chat Completions を使用します（gpt-4o-mini を想定）。API キーの設定に注意してください。
- ETL / 保存処理は DuckDB テーブルスキーマに依存します。実運用前にスキーマ初期化（必要なテーブル作成）を行ってください。

---

## ディレクトリ構成（概要）

（プロジェクトルート / src/kabusys 配下の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定の読み込み
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py           — 市場カレンダー管理
    - etl.py / pipeline.py             — ETL パイプライン、ETLResult
    - jquants_client.py                — J-Quants API クライアント（fetch/save）
    - news_collector.py                — RSS ニュース収集
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ定義・初期化
    - etl.py (公開インターフェース再エクスポート)
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — 将来リターン / IC / 統計サマリ 等

各モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理します（外部 API 呼び出しは jquants_client / OpenAI を経由）。

---

## 運用上の注意点

- Look-ahead bias 回避:
  - 多くの処理は target_date を明示的に受け取り、datetime.today() を直接参照しない設計です。バックテストで過去日時を指定することでデータリークを防げます。
- 冪等性:
  - jquants_client の save_* 関数や audit テーブル作成は冪等であることを意識しています（ON CONFLICT 等）。
- リトライ・フェイルセーフ:
  - 外部 API 呼び出しはリトライやフォールバック（失敗時はスキップして 0 を返す等）を行い、ETL 全体が中断しない設計です。
- セキュリティ:
  - news_collector は SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限を実装しています。
- テスト:
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

---

## よく使う API / エントリポイント（まとめ）

- ETL / データ:
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)
- 品質チェック:
  - kabusys.data.quality.run_all_checks(...)
- ニュース / AI:
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- 監査ログ:
  - kabusys.data.audit.init_audit_db(...)
  - kabusys.data.audit.init_audit_schema(...)
- 設定:
  - kabusys.config.settings (プロパティで環境変数を取得)

---

必要があれば README にサンプル .env.example、テーブルスキーマ（DDL）や docker-compose / systemd ジョブのサンプル、より詳しい使用例（ETL スケジュールや Slack 通知連携）を追加します。どの情報を優先的に追加しますか？