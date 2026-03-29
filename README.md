# KabuSys

日本株向けの自動売買／データ基盤ライブラリセット。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI（ニュースセンチメント）・研究（ファクター計算）・監査ログなど、投資アルゴリズムの基盤となる機能群を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成された Python パッケージです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を使った永続化（冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策・サイズ制限）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントおよび市場レジーム判定
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログスキーマ（シグナル → 発注 → 約定 のトレース）

設計方針として「ルックアヘッドバイアスの防止」「冪等性」「フェイルセーフ（API 失敗時の継続）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・前処理・raw_news への保存）
  - 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime: MA200 とマクロニュースの合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数 / .env の自動読み込みと Settings（必須トークン設定を提供）

---

## 要件（推奨）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他 標準ライブラリ以外の依存がある場合は pyproject.toml / requirements.txt を参照）

インストール例（仮の requirements.txt がある前提）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または最低限:
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

自動で .env（および .env.local）をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主な設定項目:

必須（Settings が要求するもの）
- JQUANTS_REFRESH_TOKEN   — J-Quants リフレッシュトークン
- KABU_API_PASSWORD       — kabuステーション API 用パスワード（発注周りで使用）
- SLACK_BOT_TOKEN         — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID        — Slack チャンネル ID

OpenAI（AI モジュールで使用）
- OPENAI_API_KEY          — OpenAI API キー（ai.score_news / ai.score_regime で参照）

任意（デフォルトあり）
- KABU_API_BASE_URL       — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH             — デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV             — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL               — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

簡易 .env.example:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（requirements.txt / pyproject.toml がある想定）
4. プロジェクトルートに `.env` を作成し、上記の必須変数を設定
5. DuckDB データフォルダを作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```
6. （オプション）監査用 DB を初期化:
   - Python REPL / スクリプトで実行例:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)  # settings.duckdb_path は Path
     conn.close()
     ```

---

## 使い方（代表的な例）

- DuckDB 接続作成（settings を利用）:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日（Settings.env に依らず date.today()）が対象
print(result.to_dict())
```

- ニュースセンチメントスコア取得（AI）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（MA200 + マクロニュース）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究モジュール）:

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 品質チェック一括実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # target_date を指定してスコープを限定可能
for i in issues:
    print(i)
```

注意: AI 関連関数（score_news, score_regime）は OpenAI API 呼び出しを含むため、OPENAI_API_KEY を環境変数で設定するか、api_key 引数で明示的に渡してください。API 呼び出し時のエラーはフェイルセーフとして一部処理をスキップし続行する設計です（ログに警告が出ます）。

---

## ディレクトリ構成

主要ファイル / モジュールのツリー（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースのセンチメント解析（score_news）
    - regime_detector.py    -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（fetch / save 系）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult 再エクスポート
    - news_collector.py     -- RSS 収集・前処理
    - calendar_management.py-- 市場カレンダー管理（is_trading_day 等）
    - quality.py            -- データ品質チェック
    - stats.py              -- zscore_normalize 等
    - audit.py              -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    -- momentum/value/volatility の計算
    - feature_exploration.py-- forward returns / IC / summary / rank
  - research/... (上記ファイル群)

各ファイルはモジュール単位で責務が分離されており、ETL / データ管理・研究・AI 評価・監査ログそれぞれを独立してテスト・運用できる設計です。

---

## 運用上の注意点

- KABUSYS_ENV が `live` の場合、実際の発注など重大な操作を行う可能性があります。必須の環境変数やパスワードの取り扱いは厳重にしてください。
- DuckDB の操作はトランザクション管理を行っていますが、初期化やスキーマ作成の際に transactional フラグを用途に応じて使い分けてください（audit.init_audit_schema など）。
- J-Quants API のレート制限や OpenAI のレート制限に注意。jquants_client と AI モジュールはリトライ／レート制御のロジックを持ちますが、運用側でも呼び出し頻度を管理してください。
- ニュース収集では外部 RSS 取得時の SSRF 対策・最大受信サイズ制限・XML の安全パーシング（defusedxml）を実装していますが、ソースの追加時は信頼性を検討してください。

---

## テスト / 開発

- 各モジュールは外部 API 呼び出し部分を差し替え可能（モック可能）な設計になっています（例: news_nlp._call_openai_api を unittest.mock.patch で差し替え）。
- 環境変数自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで環境を汚したくない場合など）。

---

必要であれば、README にサンプルの .env.example、docker-compose によるローカル実行例、CI のテスト手順や pyproject.toml / requirements.txt の推奨内容などを追記できます。どの情報を補足しましょうか？