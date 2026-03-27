# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集と LLM によるニュースセンチメント、ファクター計算、監査ログ（発注/約定追跡）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムやリサーチ環境のための共通ユーティリティ群です。主な目的は以下：

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・品質チェック・ETL パイプライン
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント（銘柄別）算出
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量探索・統計ユーティリティ
- 発注〜約定の監査ログスキーマ初期化ユーティリティ

設計上の共通方針として「ルックアヘッドバイアス防止（日付は明示的に渡す）」「冪等性」「フォールバックとフェイルセーフ」を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API との取得・保存（差分取得/ページネーション/リトライ/レート制御）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・正規化・保存（SSRF 対策・サイズ制限等）
  - calendar_management: 営業日・SQ判定・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化（init_audit_schema / init_audit_db）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数管理（.env 自動読み込み機能、必須変数チェック）

---

## 必要条件

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを参照してください。上記はコードから明示される主な依存です。）

---

## セットアップ手順

1. リポジトリをクローン／入手

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用に）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン（使用する場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID
- KABU_API_PASSWORD: kabuステーション等の API パスワード（使用する場合）

任意（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI 呼び出し用 API キー（ai モジュールで使用）

例: .env（簡易）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABU_API_PASSWORD=your_kabu_password
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトからの利用例です。全ての関数は明示的に DuckDB 接続や target_date を受け取る設計で、ルックアヘッドを防ぎます。

- DuckDB に接続して日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出（OpenAI API キーは環境変数または api_key 引数で）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 を使用）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
```

- 監査ログ DB 初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成される
```

- J-Quants API の直接呼び出し例（ID トークン取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
rows = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意:
- ai.news_nlp.score_news と ai.regime_detector.score_regime は OpenAI に依存します。環境変数 OPENAI_API_KEY を設定するか api_key 引数を渡してください。
- ETL／ニュース収集等はネットワーク IO を伴うため適切なエラーハンドリング・ログ設定のもとで運用してください。

---

## 設定と自動 .env ロード挙動

- .env 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings からは必須値取得時に未設定なら ValueError が発生します（例: settings.jquants_refresh_token）。

settings の主なプロパティ:
- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url (default: http://localhost:18080/kabusapi)
- slack_bot_token
- slack_channel_id
- duckdb_path (default: data/kabusys.duckdb)
- sqlite_path (default: data/monitoring.db)
- env / log_level / is_live / is_paper / is_dev

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント算出（score_news）
    - regime_detector.py  -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py         -- ETL パイプライン（run_daily_etl 他）
    - etl.py              -- ETLResult 再エクスポート
    - news_collector.py   -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理
    - quality.py          -- データ品質チェック
    - stats.py            -- 統計ユーティリティ（zscore_normalize）
    - audit.py            -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- IC/forward returns/summary utilities
  - research/... (その他分析用モジュール)
  - monitoring, strategy, execution, monitoring パッケージ名は __all__ に含まれているが上記の中核が実装済み

---

## 運用上の注意点

- すべての日時挙動はルックアヘッドバイアス対策が組み込まれており、target_date を明示的に渡すことを想定しています。内部で date.today() を参照しない実装が基本です（ただし一部ジョブはデフォルトで今日を使います）。
- OpenAI 呼び出しはリトライ／フォールバックロジックを備えていますが、API コストに注意してください。AI モジュールは API 失敗時に安全側（0.0 スコア等）で継続する設計です。
- J-Quants API はレート制限を厳守する実装（固定間隔スロットリング）です。
- DuckDB の executemany に関するバージョン依存の挙動（空リスト不可等）に配慮した実装になっています。
- audit.init_audit_schema は transactional フラグでトランザクション実行を選べます（DuckDB のトランザクション挙動に注意）。

---

## 連絡・貢献

- バグ報告や改善提案は Issue を立ててください。  
- セキュリティ上の脆弱性報告は直接メンテナーに連絡してください（公開 Issue での報告は避けてください）。

---

README は以上です。必要であれば、.env.example のテンプレートや docker-compose / systemd ユニット例、CI 用のテスト実行手順（ユニットテストのモック方法など）も追記できます。どの情報を優先して追加しますか？