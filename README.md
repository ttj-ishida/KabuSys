# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ニューススコアリング、監査ログ、ETL、マーケットカレンダー管理などを含む自動売買プラットフォーム用ライブラリ群です。本リポジトリは DuckDB をデータ基盤として利用し、J-Quants API / OpenAI（LLM）等と連携する設計になっています。

主な設計方針（抜粋）
- ルックアヘッドバイアス対策（内部で date.today() を盲目的に参照しない設計）
- DuckDB を用いた冪等保存（ON CONFLICT / INSERT ... DO UPDATE）
- 外部 API 呼び出しに対する堅牢なリトライ・レート制御
- ETL / 品質チェック（quality）によりデータ整合性を担保
- ニュース収集における SSRF 対策・XML の安全処理

---

## 機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save / 認証 / rate limit）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策）
  - 市場カレンダー管理（is_trading_day / next_trading_day 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ・トレーサビリティ（signal_events / order_requests / executions）
  - 統計ユーティリティ（z-score 正規化）
- ai
  - news_nlp: ニュースごとの銘柄センチメント（OpenAI を用いた JSON Mode）
  - regime_detector: MA とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- config
  - 環境変数管理（.env 自動読み込み、必須値チェック、設定ラッパ）

付帯機能:
- OpenAI（gpt-4o-mini）連携（JSON Mode を利用）
- J-Quants API 用 RateLimiter とトークン自動リフレッシュ
- DuckDB を前提としたテーブル初期化 / audit DB 初期化ユーティリティ

---

## 必要条件 / 依存ライブラリ

（例）
- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例（プロジェクトルートで）:
```
pip install -e .
# または必要パッケージ個別に
pip install duckdb openai defusedxml
```

（実際の requirements.txt / pyproject.toml があればそちらを参照してください）

---

## 環境変数（主要）

プロジェクトは .env ファイルまたは環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動ロードを無効にするには環境変数を設定してください:
```
KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な変数（README 用サンプル）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知連携用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視プロセス関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

※ .env.example がリポジトリにある場合はそれを参考に .env を作成してください（コード中に .env.example 参照の記述あり）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. パッケージをインストール
   ```
   pip install -e .
   # または
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - あるいは環境変数を直接エクスポート
5. DuckDB の初期化（監査テーブル等）:
   Python REPL で:
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(str(settings.duckdb_path))
   # または既存接続に対して
   # conn = duckdb.connect(str(settings.duckdb_path))
   # from kabusys.data.audit import init_audit_schema
   # init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要な API と実行例）

以下は簡単な Python スニペット例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る（設定された DUCKDB_PATH を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務を一括取得して品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示するか環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査データベース初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)
```

- ファクター計算 / リサーチ系の利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- OpenAI 呼び出しは JSON Mode を期待しており、レスポンスパースに失敗した場合はフォールバック（0.0）する実装が多く含まれます。API キー・使用料金に注意してください。
- J-Quants API はレート制限・トークンリフレッシュロジックを組み込んでいます。JQUANTS_REFRESH_TOKEN を必ず設定してください。

---

## ディレクトリ構成（主なファイル・モジュール）

（パスは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save/get_id_token）
    - pipeline.py             — ETL パイプライン（run_daily_etl 他）
    - etl.py                  — ETLResult 再エクスポート
    - news_collector.py       — RSS ニュース収集（fetch_rss 等）
    - calendar_management.py  — 市場カレンダー管理 / calendar_update_job
    - quality.py              — データ品質チェック（check_missing_data 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログテーブル定義 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility 等
    - feature_exploration.py  — forward returns / IC / summaries

README で触れていない細かいユーティリティや内部 API は各モジュールの docstring を参照してください（各関数に詳細な説明あり）。

---

## 運用・開発時の注意事項

- Look-ahead Bias（未来情報を使ってしまうこと）を避けるため、上記モジュールは target_date 引数を受け取り内部で現在時刻を直接参照しない設計です。バックテスト用途では必ず適切な target_date を与えてください。
- DuckDB の executemany に対するバージョン差異（空リスト渡し不可等）を考慮した実装があります。DuckDB のバージョン互換性に注意してください。
- ニュース収集は外部 RSS の取得を行うため、SSRF や XML インジェクション対策（defusedxml）等が実装されています。外部 URL を扱う際は設定とネットワークポリシーに注意してください。
- 自動環境読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用します。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して静的に環境を注入してください。

---

## 開発者向け / テスト

- モジュール内の外部 API 呼び出し（OpenAI / urllib / J-Quants）には差し替えやモックが行えるように設計されています（内部の _call_openai_api や _urlopen 等を unittest.mock.patch で差し替え可能）。
- ETL / 品質チェックは個別に実行して結果を検査できるため、ユニットテスト・統合テストの切り分けが容易です。

---

必要に応じて README にサンプル .env.example、起動用スクリプト、DB スキーマ初期化手順を追加することを推奨します。質問や追加したいセクション（例: Docker、CI、具体的なテーブルスキーマ一覧）があれば教えてください。