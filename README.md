# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（注文から約定のトレーサビリティ）などの機能を提供します。

## 主な特徴
- J-Quants API 経由の差分取得・保存（株価・財務・上場情報・市場カレンダー）
  - レートリミット制御、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（差分取得 + 品質チェック）
- ニュース収集（RSS）と前処理、銘柄紐付け
  - SSRF / Gzip / サイズ上限などを考慮した堅牢な実装
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（ai.news_nlp）
  - 銘柄ごとの ai_score を ai_scores テーブルへ書き込み
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価を合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化・管理（DuckDB）

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env 自動読み込み（.env, .env.local）・環境変数ラッパ
- kabusys.data
  - jquants_client: API 取得・保存
  - pipeline: run_daily_etl 等の ETL 実装（ETLResult を返す）
  - news_collector: RSS 収集・前処理
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: ニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: 市場レジーム判定を実行して market_regime に書き込む
- kabusys.research
  - ファクター計算（momentum / value / volatility 等）、特徴量探索ユーティリティ

---

## 前提（要件）
- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml（ニュース XML パース用）
- ネットワークアクセス（J-Quants, RSS ソース, OpenAI）

（requirements.txt / pyproject.toml は別途プロジェクトに応じて準備してください）

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローンして editable インストール（例）
   - git clone <repo>
   - cd <repo>
   - pip install -e ".[dev]"  # 実際の extras 名はプロジェクトに合わせて

2. .env を準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

3. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化・簡単な使い方（コード例）
以下は Python REPL / スクリプトから利用する最小の例です。

1) DuckDB 接続準備（設定値を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ DB の初期化（監査用 DB を独立して作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可能
# または既存 conn にスキーマを追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

3) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date None -> 今日
print(result.to_dict())
```

4) ニュースセンチメントのスコアリング（ai_scores へ書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

5) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

注意:
- AI 関連関数は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を要求します。
- これらの関数は DuckDB 上の所定テーブル（raw_news, prices_daily, market_regime 等）を前提に動作します。事前に ETL でデータを投入してください。

---

## よく使うユーティリティ
- settings（kabusys.config.settings）: アプリ設定の参照ラッパ
  - settings.duckdb_path / settings.sqlite_path / settings.is_live など
- ETLResult（kabusys.data.ETLResult）: run_daily_etl の戻り値（品質問題やエラー情報を含む）
- quality.run_all_checks: データ品質チェックをまとめて実行

---

## 自動 env ロードの挙動
- 優先順位: OS 環境変数 > .env.local > .env
- パッケージ読み込み時に、プロジェクトルート（.git または pyproject.toml を探索）を基に自動読み込みします。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - audit/ (なし：ファイルは audit.py にまとまっています)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*: ファクター計算・特徴量解析ユーティリティ
- その他: strategy / execution / monitoring を __all__ に含めていますが、実装はこのコードベースの別モジュールで提供されます（将来的な拡張領域）

（上記は本リリースに含まれる主要モジュールの抜粋です）

---

## 運用上の注意
- 実口座（live）環境での運用時は settings.is_live を用いてチェックを入れてください（paper_trading / live 切替）。
- OpenAI 呼び出しは料金とレートリミットに注意してください。AI 関連メソッドはリトライやフォールバック（API失敗時はスコア0）等が組み込まれていますが、設計上は外部 API の安定性に依存します。
- J-Quants API のレート制限を厳守する実装になっていますが、長時間のバッチや多数の並列クライアントで使用する場合はさらに調整してください。
- DuckDB バージョン差異（executemany の空リスト挙動など）に注意して実装されていますが、運用環境の duckdb バージョンを合わせてください。

---

## 開発・貢献
- コードは可読性と堅牢性を重視しており、ユニットテスト、モック差し替えポイントが設けられています（例: API 呼び出しラッパをモック）。
- バグ修正・機能追加の際は、テストを追加し、.env.example を更新してください。

---

必要であれば、README に以下も追記できます：
- 実行例のより詳しいスクリプト（cron / Airflow 用のラッパ）
- .env.example のテンプレート
- 各テーブルスキーマの一覧（raw_prices / raw_news / ai_scores / market_regime / market_calendar / raw_financials など）
- CI / テスト実行方法

追加してほしい項目があれば教えてください。