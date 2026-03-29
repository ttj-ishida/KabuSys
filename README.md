# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータ基盤として、J-Quants API からの ETL、ニュース収集と LLM ベースのニュースセンチメント判定、マーケットレジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（オーディット）機能などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しないなど）
- ETL/保存は冪等（idempotent）に実装（ON CONFLICT / DELETE→INSERT 等）
- 外部 API の呼び出しはリトライ・バックオフ・フェイルセーフ実装
- テスト容易性を意識した実装（API 呼び出し点をモック可能）

---

## 機能一覧

- データ ETL / 管理
  - J-Quants からの株価日足（OHLCV）・財務データ・マーケットカレンダー取得（`kabusys.data.jquants_client`）
  - 日次 ETL パイプライン（差分取得・バックフィル、品質チェック）（`kabusys.data.pipeline.run_daily_etl`）
  - カレンダー管理（営業日判定、next/prev/trading days）（`kabusys.data.calendar_management`）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）（`kabusys.data.quality`）
  - ニュース収集（RSS → `raw_news`/`news_symbols`）（`kabusys.data.news_collector`）
  - 監査ログ用スキーマ初期化 / DB（`kabusys.data.audit`）

- AI / NLP
  - ニュースの銘柄別センチメントスコア算出（OpenAI を使用）（`kabusys.ai.news_nlp.score_news`）
  - マクロ + ETF MA200 を合成した市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）

- リサーチ（factor / feature）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（`kabusys.research`）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー（`feature_exploration`）
  - Zスコア正規化などの統計ユーティリティ（`kabusys.data.stats.zscore_normalize`）

- 設定管理
  - .env または環境変数から設定を自動ロード（パッケージルートに .git / pyproject.toml を基準に探索）（`kabusys.config.settings`）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法などを使用）
- DuckDB のバイナリが利用可能な環境

1. リポジトリを取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Linux/macOS）
   - .venv\Scripts\activate（Windows）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - 推奨（開発時）: pip install -e . も可能（パッケージが setup/pyproject を用意している前提）

   代表的な依存パッケージ（最低限）:
   - duckdb
   - openai
   - defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（News NLP / Regime）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite path for monitoring DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment (development|paper_trading|live)（デフォルト: development）
   - LOG_LEVEL: (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   .env のサンプル（プロジェクトに `.env.example` を置いている想定）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表例）

下記は最小限の使用例です。各関数は DuckDB 接続を受け取り、トランザクション制御は関数内部で行われる場合があります。

1) 設定と DB 接続の準備
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーを環境変数に設定済みなら api_key は不要
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書込銘柄数: {n_written}")
```

4) 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) ファクター計算（リサーチ）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

6) 監査ログスキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
# 以後 audit_conn を使って監査テーブルへアクセス
```

注意点：
- OpenAI 呼び出しには `OPENAI_API_KEY`（または各関数の api_key 引数）が必要です。API 呼び出しはリトライ/フェイルセーフを持ちますが、キーがないと例外になります。
- DuckDB のスキーマ（テーブル群）は別途初期化コードがある想定です（ETL を実行するときに必要なテーブルが未作成ならエラーになります）。プロジェクトに schema 初期化スクリプトがある場合はそちらを使ってください。

---

## 自動 .env ロードの挙動

- パッケージロード時にプロジェクトルート（src/kabusys/config.py の位置から親ディレクトリで .git または pyproject.toml を探索）を特定し、以下の順で環境変数をロードします：
  1. OS 環境変数（既存のものは保護）
  2. .env（未設定のキーのみセット）
  3. .env.local（既存値を上書き。ただし OS 環境変数は保護されます）

- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト向け）。

- 必須変数が参照された場合、未設定だと `ValueError` が発生します（例: JQUANTS_REFRESH_TOKEN を settings.jquants_refresh_token が参照したとき）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
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
      - stats.py
      - quality.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (存在宣言のみ in __all__ としているが実装は省略されている場合あり)
    - strategy/ (同上)
    - execution/ (同上)

リポジトリ上のファイルは上の README に含まれているモジュール群を中心に構成されています。実際のプロジェクトではさらにテスト、スクリプト、設定ファイル（.env.example、pyproject.toml 等）が存在する想定です。

---

## 開発・貢献

- テスト可能性を考慮して、外部 API 呼び出しの入る関数（OpenAI / urllib / J-Quants）をモックできるように実装されています。ユニットテストを書く際は該当関数（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.news_collector._urlopen など）を patch して振る舞いを差し替えてください。
- 変更を加える場合は型注釈・ドキュメント文字列を維持してください。多くの関数は外部副作用（DB書き込み、外部API）を伴うため、必ず安全にロールバックを行う実装が行われています。

---

もし README に追加してほしい具体的な実行例（cron ジョブの例、Docker/Compose 構成、CI 設定、スキーマ初期化 SQL など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt も作成します。