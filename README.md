# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ（KabuSys）の README。  
本リポジトリはデータ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクターリサーチ、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買（および研究）に必要な次の機能をモジュール化して提供します。

- J-Quants API を用いた株価・財務・市場カレンダーの差分 ETL（idempotent 保存・品質チェック付き）
- RSS ベースのニュース収集と前処理（SSRF / サイズ制限 / トラッキング除去 等に配慮）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント算出（銘柄別 ai_score）とマクロセンチメントを用いた市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ（IC / forward returns 等）
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化ユーティリティ
- 設定管理（.env の自動読み込み / Settings API）、ロギングレベルや環境判定フラグ

設計方針として、バックテストでのルックアヘッド（未来参照）を防ぐ実装、API リトライ・レート制御、DB への冪等保存、そしてフェイルセーフ（API 失敗時はスキップして継続）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得関数 + DuckDB 保存関数）
  - pipeline / etl: 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 取得と raw_news への保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ用スキーマ作成・DB 初期化
  - stats: 汎用統計（z-score 正規化等）
- ai/
  - news_nlp: 銘柄別ニュースをまとめて OpenAI に送信し ai_scores に保存（score_news）
  - regime_detector: ETF（1321）の MA とマクロ記事の LLM センチメントを合成して market_regime を生成（score_regime）
- research/
  - factor_research: momentum / value / volatility ファクター計算
  - feature_exploration: forward returns, IC, factor summary, rank 等
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト（settings）を提供

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに | を使用）
- DuckDB、openai、defusedxml 等が必要

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   requirements.txt がある場合はそれを使ってください。なければ最低限：
   ```
   pip install duckdb openai defusedxml
   ```
   （実行環境や CI 用に他のパッケージが必要な場合があります）

4. パッケージを開発モードでインストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数の準備
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等で使用）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（基本例）

以下はパッケージ内の主要 API を使う最小例です。DuckDB 接続は duckdb.connect() を使います。

- Settings の利用（環境変数から値を読む）
```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path オブジェクト
```

- DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます（内部で営業日に調整）
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API key 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に api_key を渡すことも可能
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

- 市場レジームスコアの算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 既にテーブルがある場合は冪等で何度でも呼べます
```

- J-Quants から単発で株価を取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# id_token は get_id_token で取得され、内部でキャッシュされます
records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

注: OpenAI 呼び出しや J-Quants 呼び出しを行う関数は引数で API キーや id_token を注入できます（テストや複数トークン運用に便利）。また API 呼び出しはリトライやレート制御を行います。

---

## よく使う関数一覧（代表）

- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db / init_audit_schema(...)
- kabusys.research.factor_research.calc_momentum / calc_value / calc_volatility
- kabusys.research.feature_exploration.calc_forward_returns / calc_ic / factor_summary

---

## 設計上の注意点・運用メモ

- Look-ahead バイアス対策
  - 内部処理は原則として date.today() を直接参照せず、引数の target_date に依存するよう設計されています（バックテストでの再現性確保）。
  - DB クエリも target_date 未満・以前を明示してルックアヘッドを防いでいます。

- 冪等性
  - jquants_client の save_* 関数やニュースの保存、監査ログの DDL は冪等性を考慮して作られており、再実行しても重複を排除します（ON CONFLICT 等を利用）。

- API キー管理
  - .env に鍵を置く場合は権限管理を徹底してください。自動ロードが不要なテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると読み込みを無効化できます。

- エラー処理
  - 外部 API 呼び出しはリトライやサーキットとしてフェイルセーフが入っていますが、失敗時は該当処理をスキップして残りを継続する挙動が多く採用されています。運用時はログと quality チェックを監視してください。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイルと役割の概略です（実際のファイルはリポジトリを参照してください）。

- src/kabusys/
  - __init__.py                      - パッケージ初期化 & バージョン
  - config.py                        - .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                    - ニュースの LLM による銘柄別スコア算出（score_news）
    - regime_detector.py             - マクロ + ETF MA を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント（取得・保存）
    - pipeline.py                    - ETL パイプライン & run_daily_etl
    - etl.py                         - ETL インターフェース再エクスポート（ETLResult 等）
    - news_collector.py              - RSS 収集と前処理
    - calendar_management.py         - 市場カレンダー管理（営業日判定等）
    - quality.py                     - データ品質チェック
    - stats.py                       - 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                       - 監査ログスキーマ初期化/DB 初期化
  - research/
    - __init__.py
    - factor_research.py             - Momentum / Value / Volatility 等
    - feature_exploration.py         - forward returns / IC / summary / rank

---

## 開発・テスト

- 自動テストや CI の設定はリポジトリに依存します。外部 API 呼び出し部分はモック化して単体テストを行ってください（コード内でモックポイントを想定しています）。
- OpenAI 呼び出しは unittest.mock.patch() で _call_openai_api 等を差し替える設計になっています。

---

必要に応じて README にサンプル .env.example、CI 用の設定や具体的な SQL スキーマ定義（テーブル定義）を追加できます。追加してほしいサンプルや運用手順があれば教えてください。