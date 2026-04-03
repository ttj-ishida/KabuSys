# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI によるセンチメント評価）、ファクター計算、監査ログ（約定トレーサビリティ）、マーケットカレンダー管理など、バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務情報、マーケットカレンダー取得（差分取得・ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT 相当の更新）
  - ETL の一括実行（run_daily_etl）と個別実行（run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集・NLP
  - RSS からニュースを収集して raw_news テーブルへ保存（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（score_news）
  - マクロニュース + ETF（1321）200日 MA 乖離を組み合わせた市場レジーム判定（score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、Information Coefficient（IC）計算、ファクター統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマ定義と初期化ユーティリティ（init_audit_schema, init_audit_db）
  - 発注フローを UUID で追跡できる設計

- 設定管理
  - 環境変数／.env の自動読み込み（プロジェクトルート検出）と Settings オブジェクトによるアクセス（kabusys.config.settings）

---

## セットアップ手順（開発者向け）

前提
- Python 3.10+（typing における | 型表記を利用）
- 仮想環境の使用を推奨（venv / pyenv など）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   ※requirements.txt がある場合はそれを使用してください。想定される依存：
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリのみで実装されている部分も多いですが、上記は必須機能に必要です）
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数 / .env

- 自動ロード
  - パッケージはインポート時に、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` 上書きします。
  - 自動ロードを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- 主要な環境変数（必須／任意）
  - 必須（未設定だと Settings で ValueError）
    - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
    - KABU_API_PASSWORD : kabuステーション API 用パスワード（発注機能を使う場合）
  - 任意 / 使用する機能に依存
    - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知連携
    - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
    - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
    - KABUSYS_ENV :環境 ("development" / "paper_trading" / "live")（デフォルト development）
    - LOG_LEVEL : ログレベル ("DEBUG"/"INFO"/...、デフォルト INFO)

- .env のパース仕様
  - export KEY=val 形式をサポート
  - シングル/ダブルクォートとバックスラッシュエスケープを考慮
  - # がコメント扱いになるルールは実装に従います

例（.env）:
```
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API の例）

以下はコードから直接利用する場合の簡単な例です。基本的に DuckDB 接続を生成して各モジュール関数に渡します。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントスコア（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定済みか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

4) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

6) ファクター / リサーチユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value
from kabusys.data.stats import zscore_normalize

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
z_momentum = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API キーやレート制限に注意してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、内部で空チェックが行われています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数・設定管理（自動 .env ロード、Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのセンチメント化（score_news）
  - regime_detector.py — マクロ + ETF MA による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得／保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETL インターフェース（ETLResult 再エクスポート）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - news_collector.py — RSS ニュース収集（SSRF 対策、前処理）
  - calendar_management.py — マーケットカレンダー管理・営業日判定
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum, volatility, value）
  - feature_exploration.py — 将来リターン・IC・統計サマリー 等

その他（パッケージルート）
- .env / .env.local（プロジェクトルートに置いて使用）
- pyproject.toml / setup.cfg 等（プロジェクトに合わせて用意）

---

## 開発・運用上の注意

- Look-ahead バイアス対策
  - 多くの関数は date の引数を明示的に受け取り、date.today() などを不用意に参照しないよう設計されています。バックテストで使用する場合は「対象日の情報のみ」を使うこと。

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants 等）エラー時は可能な限りフォールバック（スコア 0.0、処理スキップ）して、全体の処理継続を優先します。ログで障害を確認してください。

- レート制限
  - J-Quants のレート制限（120 req/min）に合わせた内部 RateLimiter を備えています。OpenAI 呼び出しでもリトライ・バックオフを実装していますが、運用時はレートに注意してください。

- セキュリティ
  - news_collector は SSRF 対策、XML 脆弱性対策（defusedxml）を実装しています。RSS ソースは信頼できるものを設定してください。

---

## 貢献・拡張

- 新しい ETL ソースやニュースソースの追加、発注実装（kabu ステーション連携）など、モジュール設計は拡張しやすいよう疎結合に配慮してあります。
- テストでは Settings の自動 .env 読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を活用してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細な API リファレンスや CLI コマンド、運用手順（systemd サービス例・監視方法）なども作成します。どの情報を追加しますか？