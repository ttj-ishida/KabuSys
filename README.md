# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、データ品質チェック、ニュース収集・NLP（OpenAI 経由）による銘柄センチメント算出、研究用ファクター計算、監査ログ（発注トレース）などを含みます。

---

## プロジェクト概要

KabuSys は以下のような機能群を提供する Python パッケージです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分 ETL（取得 → DuckDB 保存）
- Data 品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集（raw_news）と銘柄紐付け
- ニュースを LLM（OpenAI）で解析して銘柄ごとの ai_score を生成
- マクロセンチメントと ETF MA を組み合わせた市場レジーム判定
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログスキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- 設定 / 環境変数管理（.env 自動読み込み等）

設計上の主な方針：
- ルックアヘッドバイアスの防止（内部処理で date.today()/datetime.today() に依存しない）
- DuckDB を使ったローカルデータストア / 冪等保存（ON CONFLICT）
- OpenAI 等の外部 API 呼び出しはリトライ・フェイルセーフ実装
- テスト容易性のため内部 API 呼び出しをモック可能に設計

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証トークン自動リフレッシュ、レート制御）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days など）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date) — LLM によるニュースセンチメント算出 → ai_scores へ書き込み
  - regime_detector.score_regime(conn, target_date) — ETF MA とマクロニュースを組合せて market_regime を算出
- research/
  - factor 計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析 utilities（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env ファイル（.env/.env.local）自動読み込み、必須環境変数チェック

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の union operator `|` 等を使用）
- 仮想環境の利用を推奨

1. リポジトリをクローンして移動
   ```
   git clone <このリポジトリ>
   cd <リポジトリ>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール
   - 最低限の依存例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用／テスト用のパッケージがあれば適宜追加してください（pytest など）。

4. 開発モードでインストール（パッケージとして使う場合）
   ```
   pip install -e .
   ```
   （pyproject.toml / setup.py がある場合）

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
   - あると便利な変数（オプション・デフォルトは config.Settings を参照）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を実行する場合）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB 保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - LOG_LEVEL, KABUSYS_ENV, PID_FILE_PATH, など多数（config.Settings に全リストあり）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

以下はライブラリの代表的な使用例です。実行環境・DB は事前に用意してください。

1) 日次 ETL を実行（ETL パイプライン）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI を使う）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```
- OpenAI API キーは引数 api_key に渡すか、環境変数 OPENAI_API_KEY を設定します。

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

テスト時の注意
- OpenAI 呼び出しを含む関数は内部でモジュールローカルの呼び出し関数を使うため、unittest.mock.patch で差し替えてテストしやすく設計されています（例: patch("kabusys.ai.news_nlp._call_openai_api")）。

---

## 主な設定 / 環境変数

（抜粋、config.Settings を参照して下さい）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

自動 env ロードについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env.local は既存の OS 環境変数を上書きしますが内部で保護されています。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 配下の主要モジュール群です（抜粋）。

- src/kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - (その他 ETL 補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...
  - monitoring/         # 監視関連（README には抜粋）
  - strategy/           # 戦略層（信号生成）
  - execution/          # 発注実行・kabu API 統合

（実際のツリーはリポジトリ内の `src/kabusys` を参照してください）

---

## 開発者向けメモ / 注意点

- Python バージョン: 3.10 以上推奨（`X | Y` 型注釈を使用）
- DuckDB バージョンによる executemany の挙動差異に注意（コード内で互換性確保済み）
- OpenAI 呼び出しは JSON Mode を前提にレスポンスを厳密にパースしています。実運用では API レスポンスの変化に注意してください。
- ニュース収集は SSRF 対策（ホストのプライベート判定、リダイレクト検査）や XML の安全パーシング（defusedxml）を行っています。
- ETL / 監査スキーマは冪等性を意識しているため、再実行・部分失敗時のデータ破壊リスクは低めです。

---

## よくある操作コマンド例

- 開発依存インストール（例）
  ```
  pip install -r requirements.txt
  ```
  （requirements.txt が無ければ手動で duckdb / openai / defusedxml を入れてください）

- パッケージを編集可能インストール
  ```
  pip install -e .
  ```

---

README に書かれていない詳細や、特定機能の利用例（例: strategy 層の API、kabuステーション連携）のサンプルをご希望の場合は、どの機能についての利用例が欲しいかを教えてください。必要に応じて具体的なコード例やワークフローを追加します。