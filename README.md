# KabuSys

日本株向け自動売買・データプラットフォームライブラリ。  
ETL、ニュース収集・NLP（LLM連携）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注/約定トレーサビリティ）などを含むモジュール群を提供します。

主に DuckDB をデータ層に使い、J-Quants API / RSS / OpenAI（gpt-4o-mini）など外部サービスと連携してデータ取得・解析・監視を行う設計です。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価（OHLCV）、財務、マーケットカレンダーの差分取得（ページネーション・レート制御・リトライ付き）
  - ETL 統合ジョブ（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ保存は DuckDB へ冪等 (ON CONFLICT DO UPDATE)

- ニュース収集・NLP
  - RSS フィードからニュース記事収集（SSRF対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）で銘柄別センチメントスコアを生成し `ai_scores` に保存（score_news）
  - LLM 呼び出しはリトライ・JSON 検証を実装、失敗時は安全にフォールバック

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュース（LLMセンチメント）を合成して日次レジーム（bull/neutral/bear）判定（score_regime）

- 研究用ファクター計算
  - Momentum / Volatility / Value 等の定量ファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー、Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損、重複、将来日付、スパイク等の検出と QualityIssue レポート（run_all_checks）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（init_audit_schema / init_audit_db）
  - 発注フローの UUID 連鎖とタイムスタンプ管理

- 設定管理
  - .env（.env.local）または環境変数から設定を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - settings オブジェクト経由でアクセス（例: settings.jquants_refresh_token）

---

## 前提・依存関係

- Python 3.10+
- 必須外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクトに requirements.txt / pyproject.toml がある想定）:
```bash
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 開発中: ローカルパッケージとしてインストール
python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置

2. 依存パッケージをインストール（上記参照）

3. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合は無効）。
   - 主要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   - サンプル `.env`（最低限）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ準備
   - ETL や audit モジュールは想定されるテーブルが存在することを前提に動作します。必要に応じてスキーマ初期化用のスクリプトを用意してください（本コード内に audit 初期化ユーティリティあり: init_audit_schema / init_audit_db）。

---

## 使い方（主な API / 実行例）

以下では Python REPL やスクリプトからの利用例を示します。適切に環境変数を設定してから実行してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成して ai_scores に保存（OpenAI APIキーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
# api_key を明示的に渡すことも可能: score_news(conn, date, api_key="sk-...")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "records")
```

- 設定アクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

注意点:
- LLM（OpenAI）呼び出しは API 制限や料金が発生します。テスト時は api_key をモックしてください。
- ETL / API 呼び出しは外部ネットワークに依存するため、実行環境のネットワーク設定や API レートに注意してください。

---

## 主要なモジュール・ディレクトリ構成

リポジトリの主要なファイル・フォルダ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースセンチメントスコア（score_news）
    - regime_detector.py  : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（fetch_* / save_*）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - etl.py              : ETLResult の再エクスポート
    - news_collector.py   : RSS 収集 / 前処理
    - quality.py          : データ品質チェック
    - stats.py            : 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - audit.py            : 監査ログ（監査テーブルの DDL / init）
  - research/
    - __init__.py
    - factor_research.py  : Momentum / Volatility / Value 等
    - feature_exploration.py : 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ 以下にさらにサブユーティリティが多数

（実際のプロジェクトでは top-level に pyproject.toml / requirements.txt / .env.example 等がある想定）

---

## トラブルシューティング / 注意事項

- 自動環境変数読み込み:
  - package インポート時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストや CI で便利）。

- OpenAI 呼び出し:
  - JSON mode を利用して厳密な JSON を期待していますが、API の応答が必ずしも完全ではないためパース失敗時はフォールバックします（score_news / score_regime は失敗時に 0.0 等で継続します）。

- J-Quants API:
  - レート制限や 401 リフレッシュロジックを持っています。`JQUANTS_REFRESH_TOKEN` は必須です。

- DuckDB 互換性:
  - 一部の executemany の挙動や配列バインドは DuckDB のバージョンに依存しやすいため、pipeline や ai モジュールは互換性を考慮して実装されていますが、DuckDB バージョンにより挙動が変わる可能性があります。

---

## 貢献・開発

- 単体テストやモックを使った外部 API のテストが重要です。LLM / ネットワーク呼び出しはテスト時に差し替えられるよう設計されています（内部の _call_openai_api 等をモック）。
- 新しい ETL ジョブや保存スキーマを追加する際は、冪等性（ON CONFLICT）と品質チェックを必ず考慮してください。

---

この README はコードベース（src/kabusys）に基づく概要と利用ガイドです。詳細なスキーマ定義・運用手順・デプロイ手順は別途ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README をより詳しく、あるいは運用手順書に展開します。