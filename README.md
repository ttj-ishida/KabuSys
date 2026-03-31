# KabuSys

日本株向けのデータプラットフォーム / リサーチ / 自動売買基盤の軽量実装セットです。  
DuckDB を中心としたローカルデータレイク、J-Quants からの ETL、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定、研究用ファクター計算、監査ログなどを含みます。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を用いたローカル永続化（冪等保存）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- モジュール単位でテスト差し替え（関数のモックが容易）

---

## 機能一覧

- data
  - ETL パイプライン（J-Quants からの差分取得、保存、品質チェック）
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（認証・ページネーション・保存関数）
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 市場カレンダー管理（営業日判定 / next/prev trading day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限対策、URL 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ（signal_events / order_requests / executions テーブルの生成、init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（gpt-4o-mini を使った銘柄別センチメント: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメント: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns, IC（Spearman）, 統計サマリ）
- config
  - .env / 環境変数の自動ロード（プロジェクトルートを自動検出）
  - Settings オブジェクトで設定値を集約

---

## 要求環境 / 依存

- Python 3.10+
- 必要ライブラリ（抜粋）
  - duckdb
  - openai
  - defusedxml
- （プロジェクトで利用する実行環境に応じて追加ライブラリや CLI ツールが必要になる可能性があります）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# プロジェクト配布形式に応じて:
# pip install -e .
```

---

## 環境変数 / .env

自動的にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須は README 内で明記）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime の API キー。関数呼び出し時に api_key 引数でも指定可能)
- Slack（通知等に使用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス（任意）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
  - LOG_LEVEL (DEBUG|INFO|...、デフォルト: INFO)

設定は Settings オブジェクト経由で参照できます:
```py
from kabusys.config import settings
print(settings.duckdb_path)
```

.env のパースはシェルライク（export KEY=val, クォート、コメント抑制の細かい動作あり）です。

---

## セットアップ手順（ローカルで使い始める最小手順）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt があれば:
   # pip install -r requirements.txt
   ```

4. .env を作成して必要な環境変数を設定
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB ファイルの準備（デフォルトパスにディレクトリがなければ自動作成されます）
   - 監査用 DB を初期化したい場合:
   ```py
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ作成されスキーマを初期化
   conn.close()
   ```

---

## 使い方（代表的な API とサンプル）

- DuckDB 接続の作成例:
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄センチメント（score_news）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定するか api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定（score_regime）
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- 研究用ファクター計算（例: momentum）
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

- 監査ログスキーマ初期化（既存 DuckDB に追加）
```py
from kabusys.data.audit import init_audit_schema

# 既存 conn を渡して監査スキーマを作る
init_audit_schema(conn, transactional=True)
```

- 市場カレンダー操作の例
```py
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- J-Quants クライアント直接利用例
```py
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意:
- score_news / score_regime は OpenAI を利用するため API キーと利用料が必要です。失敗時はフェイルセーフでスコアをゼロ扱いする振る舞いが多く採用されていますが、API 制限により処理がスキップされる場合があります。
- ETL / 保存関数は DuckDB に対して冪等（ON CONFLICT DO UPDATE）で動作します。

---

## ディレクトリ構成（主要ファイル）

概要 (src/kabusys):

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント取得（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント / 保存ロジック
    - pipeline.py — ETL（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック
    - stats.py — 汎用統計（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 計算
    - feature_exploration.py — forward returns / IC / factor summary

---

## 実運用上の注意

- 本コードベースは自動売買システムの一部を構成します。実際の発注処理（ブローカー API 呼び出し）や資金管理・リスク管理ロジックは別途慎重に実装・レビューしてください。
- OpenAI を利用する部分はコストとレイテンシ、API 制限を考慮して運用してください（バッチ化、レート制御）。
- 環境依存の設定（秘密トークン等）は .env / 環境変数で管理し、バージョン管理にコミットしないでください。
- DuckDB ファイルのバックアップや監査ログの保持ポリシーは運用方針に合わせて検討してください。

---

もし README に追加したいサンプル（例えば具体的な ETL ワークフロースクリプト、ユニットテストの実行方法、CI設定例など）があれば教えてください。必要に応じて追記・整形します。