# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、監査ログ（発注・約定トレーサビリティ）などを備えた内部ライブラリ群です。バックテスト／リアル運用の前段処理（ETL）やリサーチ、AI を活用したシグナル生成の基盤を提供します。

主な特徴
- J-Quants API からの差分取得・ページネーション対応・リトライ・レートリミット対応
- DuckDB を用いた ETL 保存（冪等保存：ON CONFLICT DO UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）およびマクロセンチメント評価
- 市場レジーム（bull/neutral/bear）判定
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- 監査ログ用スキーマ初期化ユーティリティ（監査テーブル・インデックス、監査 DB 初期化）

---

## 機能一覧（抜粋）

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須設定の取得とバリデーション（kabusys.config.Settings）

- データ（kabusys.data）
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - pipeline: 日次 ETL パイプライン（run_daily_etl、個別 ETL ）
  - etl/ETLResult: ETL 実行結果オブジェクト
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 取得・前処理・raw_news 保存用ユーティリティ
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - audit: 監査ログスキーマ生成・監査 DB 初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化などの統計ユーティリティ

- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント生成・ai_scores 保存
  - regime_detector.score_regime: マクロセンチメント + ETF MA200 乖離を合成した市場レジーム判定

- Research（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を用いた正規化ユーティリティ

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要パッケージ（抜粋）:
  - duckdb
  - openai（SDK、OpenAI API 呼び出し用）
  - defusedxml
  - （ネットワークアクセス、J-Quants / OpenAI API キーが必要）
- (任意) ローカルでのデータ永続化に DuckDB ファイルを使用

requirements.txt がない場合は上記ライブラリを pip でインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数（主要）

kabusys.config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() により idToken を取得します。
- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード（運用・実行系で使用）。
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 関連処理で使用)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意、通知用)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, 監視用 DB)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視設定）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development | paper_trading | live) - 環境モード
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env ファイル例（.env.example を参考に作成）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env 読み込みはデフォルトで有効です。無効化する場合は環境変数で:
```
KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン（またはソースを配置）
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は少なくとも duckdb, openai, defusedxml をインストールしてください。
4. プロジェクトルートに .env を作成して必要な環境変数を設定
5. DuckDB の初期スキーマ（監査ログ等）を作成する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   または既存の DuckDB 接続を渡して init_audit_schema を実行できます。

---

## 基本的な使い方（コード例）

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# ETL を今日実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄単位）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- マーケットレジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化（ファイル作成含む）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/monitoring_audit.duckdb")
```

- ファクター計算（Research）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- ETL 実行結果の確認:
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
if res.has_errors or res.has_quality_errors:
    print("ETL に問題があります:", res.to_dict())
```

---

## 注意点 / 設計上の方針（抜粋）

- Look-ahead bias（ルックアヘッドバイアス）対策が徹底されています。関数は原則として datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡す設計が多く採用されています。
- API 呼び出しは失敗時フォールバックを行い、致命的な失敗を可能な限り局所化します（例: LLM 呼び出し失敗時はスコアを 0 にフォールバックして処理継続）。
- DuckDB への書き込みは冪等性（ON CONFLICT DO UPDATE）を意識した実装。
- news_collector は SSRF 対策・XML インジェクション対策（defusedxml）・トラッキングパラメータ除去など安全性を考慮。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュールと概要です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（J-Quants トークン、kabu API 等）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを LLM で銘柄別評価し ai_scores に書き込む
    - regime_detector.py
      - ETF(1321) MA200 乖離 + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save 関数）
    - pipeline.py
      - ETL の主要処理（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - etl.py
      - ETLResult のエクスポート
    - calendar_management.py
      - マーケットカレンダー管理・営業日判定
    - news_collector.py
      - RSS 取得・前処理・保存ロジック（SSRF 対策 等）
    - quality.py
      - データ品質チェック（欠損/スパイク/重複/日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログスキーマ定義・初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py
      - forward returns, IC, factor_summary, rank 等

---

## 開発メモ / テスト時の便利な点

- 自動 .env 読み込みが原因で環境に依存する場合は、テスト時に環境変数を無効化できます：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク I/O はユニットテストの際に差し替え可能なように内部で分離・ラップされています（例: kabusys.ai.news_nlp._call_openai_api の差し替え等）。
- DuckDB の接続には ":memory:" を渡せるため、テスト用にインメモリ DB を利用できます：
  ```python
  import duckdb
  conn = duckdb.connect(":memory:")
  ```

---

この README はコードベースから読み取れる主要な使い方と設計概念をまとめたものです。実運用の前に .env 設定、J-Quants / OpenAI の利用ポリシー、kabu API の認証・接続等を適切に構成してください。必要であれば README の補足（CLI 実行例、CI 設定、詳しいスキーマ定義など）を追加しますのでその旨を教えてください。