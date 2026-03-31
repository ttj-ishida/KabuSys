# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、ニュースセンチメント（LLM）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 要件・依存関係
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方（サンプル）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニュースの AI スコアリング
  - 市場レジーム判定
  - 監査データベース初期化
- 重要な挙動・注意点
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要
KabuSys は日本株を対象とした自動売買システムとデータプラットフォーム向けの Python モジュール群です。  
主に以下を目的としています：

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存する ETL
- RSS ニュース収集と OpenAI を用いた銘柄別・マクロセンチメント評価
- 市場レジーム（bull/neutral/bear）判定
- 研究（ファクター計算、将来リターン、IC 等）
- 発注〜約定までの監査ログ（監査用 DuckDB スキーマ）
- データ品質チェック

設計方針として「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API失敗時はスキップ）」「DuckDB を中心としたローカル永続化」を重視しています。

---

## 主な機能
- data:
  - J-Quants クライアント（取得・保存関数、ページネーション・リトライ・レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl 等）
  - 市場カレンダー管理（営業日判定、update job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に格納
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロ記事のLLMスコアを合成して market_regime に保存
- research:
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC、統計サマリーなど

---

## 要件・依存関係
- Python >= 3.10（型注釈に | を使用）
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 推奨: 仮想環境（venv / pyenv / conda 等）

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 他に必要なパッケージがあれば追加でインストールしてください
```

※ パッケージ配布（setup/pyproject）がある場合は `pip install -e .` を推奨します。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成・依存パッケージをインストール（上記参照）
3. 環境変数を設定（.env をプロジェクトルートに配置するか、システム環境変数で設定）
   - このパッケージは自動でプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を検出し、`.env` および `.env.local` を読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 使用時）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG / INFO / ...

例は下の .env.example を参照してください。

---

## 環境変数 (.env.example)
プロジェクトルートに以下のような `.env` を作成しておくと便利です（実運用ではシークレット管理に注意）。

```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-...

# kabu station
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB paths
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

補足:
- `.env.local` は `.env` より優先して上書きされます（ローカル override）。
- OS 環境変数は .env より優先されます（保護されます）。
- 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 使い方（サンプル）

以下は主要な利用例です。実行時は適切な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

共通: DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースの AI スコアリング（前日15:00JST〜当日08:30JST を対象）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に API キーを渡すこともできます（None の場合は環境変数 OPENAI_API_KEY を使用）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

3) 市場レジーム判定（ETF 1321、ma200乖離 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key 省略時は OPENAI_API_KEY を参照
```

4) 監査 DB（order/signals/executions）初期化
```python
from kabusys.data.audit import init_audit_db

# 専用の DuckDB ファイルを作る場合
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn にスキーマ追加する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

5) J-Quants からのデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
records = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

---

## 重要な挙動・注意点
- ルックアヘッドバイアス防止:
  - 多くの関数は内部で date.today() / datetime.today() を参照せず、呼び出し側が target_date を提供することでバックテスト時のリークを防ぐ設計です。
- 自動環境変数読み込み:
  - パッケージ import 時に .git または pyproject.toml を基準にプロジェクトルートを探索し `.env` と `.env.local` を読み込みます。テスト時などに無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性:
  - ETL と保存関数（save_*）は ON CONFLICT DO UPDATE 等で冪等に設計されています。
- フェイルセーフ:
  - API 呼び出し失敗時（LLM や J-Quants）は、可能な限り部分的に継続処理して致命的な例外は上位に伝播します。ログに警告/エラーが出ますので確認してください。
- DuckDB の executemany について:
  - 一部コードは DuckDB のバージョン差異を考慮し、executemany に空リストを渡さない等の実装になっています。DuckDB は推奨バージョンで使ってください。

---

## ディレクトリ構成（主要ファイル）
以下はソースの主要モジュールとファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュース NLP スコアリング（score_news）
    - regime_detector.py   -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（fetch/save）
    - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
    - etl.py               -- ETLResult 再エクスポート
    - news_collector.py    -- RSS ニュース収集
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - quality.py           -- データ品質チェック
    - stats.py             -- zscore_normalize 等
    - audit.py             -- 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py   -- モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - (その他) strategy / execution / monitoring 等のエントリ（__all__）

---

## ロギング・デバッグ
- 設定 `LOG_LEVEL`（環境変数）でログレベルを制御できます。デフォルトは INFO。
- 各モジュールは logging.getLogger(__name__) を使用しており、アプリ側でハンドラを設定すると柔軟にログが扱えます。

---

## 最後に
この README はソースコードからの抜粋にもとづく概要と使い方のガイドです。各関数・モジュールには詳細な docstring と設計注記が含まれているので、実装を使う際は該当モジュールの docstring を参照してください。必要であれば、README に追加する項目（CI / テスト実行方法、より具体的な運用手順、例外ケースの扱い等）を指示してください。