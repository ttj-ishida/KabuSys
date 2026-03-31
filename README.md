# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株データの収集・品質チェック・特徴量計算・ニュース NLP（LLM）・市場レジーム判定・監査ログといった自動売買・リサーチの基盤機能群を提供する Python パッケージです。内部データストアとして DuckDB を利用し、J-Quants API からデータを取得します。ニュース分析やレジーム判定には OpenAI（gpt-4o-mini 等）を用いる設計になっています。

設計上の方針（一部）
- ルックアヘッドバイアスを避けるため、内部で日時の自動参照を極力行わず、呼び出し側が target_date を渡す方式を採用。
- ETL・保存は冪等性（ON CONFLICT / upsert）を重視。
- API 呼び出しはリトライ・バックオフ・レート制御を内包。
- DuckDB による SQL 処理で大規模データにも対応。

---

## 機能一覧

主な機能（モジュール別）
- kabusys.config
  - .env / 環境変数の自動ロード・管理（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- kabusys.data
  - ETL パイプライン（J-Quants からの差分取得 & 保存）
  - jquants_client：J-Quants API クライアント（認証・ページネーション・保存関数）
  - news_collector：RSS 収集（SSRF・Gzip・サイズ制限対応）
  - calendar_management：JPX カレンダー・営業日判定
  - quality：データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit：監査ログ（signal / order_request / execution）スキーマ初期化
  - ETL の公開インターフェース（run_daily_etl 等）
- kabusys.ai
  - news_nlp.score_news：ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime：MA とマクロニュースを組み合わせて市場レジーム判定
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize：クロスセクション Z スコア正規化のユーティリティ

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意

2. リポジトリをクローンしてインストール（開発時）
```bash
git clone <repo-url>
cd <repo-root>
pip install -e ".[dev]"   # setup.cfg/pyproject.toml がある場合。なければ必要な依存を個別インストール
```

必須パッケージ例（該当の requirements に沿ってください）:
- duckdb
- openai
- defusedxml

手動インストール例:
```bash
pip install duckdb openai defusedxml
```

3. 環境変数を設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が有効な場合）。
- 自動ロードを無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB データベース・監査DBの初期化（必要に応じて）
- 監査用 DB を初期化する場合は後述の API を参照。

---

## 環境変数（.env 例）

主要な必須環境変数：
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD      : kabu ステーション API パスワード（注文系の統合用）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID
- DUCKDB_PATH            : DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV            : 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL              : ログレベル ("DEBUG" / "INFO" / ...)

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
- テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（主要 API）

以下はライブラリを直接使う簡単な例です。各関数は duckdb の接続を受け取る設計です。

1) DuckDB に接続する例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（J-Quants からデータを取得して DuckDB に保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（OpenAI を用いて ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（1321 の MA200 とマクロセンチメントの合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# api_key を明示的に渡すことも可能。None の場合は環境変数 OPENAI_API_KEY を参照
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

5) 監査ログ DB の初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または in-memory
# audit_conn = init_audit_db(":memory:")
```

6) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

ログ設定の例（標準ライブラリ logging）:
```python
import logging
logging.basicConfig(level=settings.log_level)
```

---

## 注意点 / 運用上のポイント

- OpenAI 呼び出しはコストとレート制限に注意してください。API キー保持・使用量管理を忘れずに。
- J-Quants API はレート制限（120 req/min）やトークン期限に注意。jquants_client はリトライ・レート制御を内包していますが運用監視を推奨します。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime 等）は ETL 実行前に用意しておく必要があります（スキーマ初期化用関数やマイグレーションが別途ある前提）。
- 自動 .env ロードの挙動は kabusys.config が担当。CI・テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境を注入してください。
- LLM 結果は外部 API に依存するため、呼び出し失敗時のフェイルセーフ（0.0 などのフォールバック値）が設計されていますが、長期運用ではエラー監視とリトライ戦略のチューニングが必要です。

---

## ディレクトリ構成

主要ファイル / モジュールの構成（src/kabusys 配下を抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (ETLResult 再エクスポート)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/__init__.py
- その他 utility / サブモジュール群

各モジュールの責務は README の機能一覧節に記載の通りです。詳細は各モジュールの docstring を参照してください。

---

追加の質問（利用方法の詳細、実運用向けの推奨構成、サンプルスキーマ、テスト戦略など）があれば教えてください。必要に応じて README にチュートリアル・スキーマ定義・docker / systemd / cron 実行例などを追記します。