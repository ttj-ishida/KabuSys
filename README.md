# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を安易に参照しない等）
- DuckDB を用いたローカル DB 中心の処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等性（ETL の ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧（概要）

- data
  - ETL パイプライン（J-Quants からの日次株価／財務／カレンダー取得）: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得・保存関数、トークン管理、レートリミッタ）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - 監査ログ初期化（signal_events, order_requests, executions のスキーマ）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（gpt-4o-mini を用いた銘柄別センチメント → ai_scores へ書込を想定）: score_news
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成）: score_regime
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー等

---

## 前提 / 必要環境

- Python 3.10 以上
- 必要なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード 等にアクセスする場合）
- J-Quants リフレッシュトークン、OpenAI API キー、kabuステーション API パスワード などの認証情報

インストール例（pip）:
```bash
python -m pip install duckdb openai defusedxml
```
※プロジェクトに requirements.txt / poetry がある場合はそちらを使用してください。

---

## 環境変数（主な設定）

自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主なキー：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu ステーションの base url（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視系 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリを取得
2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .\.venv\Scripts\activate    # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに `.env`（必要な環境変数）を作成
5. DuckDB のデータディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
6. 設定を確認:
   - 自動ロードを無効化したいとき:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主要な例）

以下は最小限の呼び出し例です。実運用ではログ設定やエラー処理を追加してください。

- DuckDB 接続を作る（設定からパスを取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得し品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの NLP スコアリング（OpenAI キーは env または引数で渡す）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None = 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算 / 研究ツールの利用例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
fwd = calc_forward_returns(conn, date(2026,3,20))
```

- 監査ログ用 DB 初期化（独立 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でも可
```

- RSS 取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
# 返り値は NewsArticle のリスト。DB への永続化は呼び出し側で行ってください（raw_news テーブルへの挿入等）。
```

---

## 自動 env 読み込みの動作

- プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します（CWD に依存しない）。
- 読込順:
  1. OS 環境変数（既存）
  2. .env （上書きしない）
  3. .env.local（上書き）
- 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 他）
    - etl.py                       — ETL 公開 API（ETLResult 再エクスポート）
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS 収集・前処理（SSRF 対策等）
    - quality.py                   — データ品質チェック（各チェック関数）
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - audit.py                     — 監査テーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - monitoring/ (監視・実行系モジュールは __all__ に含まれますが個別ファイルはここに含まれる想定)

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください）

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しはコストがかかります。テスト時はモック（unittest.mock.patch）で置き換え可能です（score_news / regime_detector の _call_openai_api を差し替えられるよう設計）。
- J-Quants API はレート制限（120 req/min）に注意。jquants_client は内部でレートリミットとリトライを実装しています。
- ETL は冪等保存（ON CONFLICT DO UPDATE）を行うため、再実行が安全です。ただしデータ品質チェックの結果は確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で安全に処理しています。呼び出し側でも空データ時のハンドリングを行ってください。
- 本ライブラリはバックテストと運用で共通に使えるよう、ルックアヘッドバイアス防止の実装を心がけています。バックテストで使用する場合はデータの取り扱いに注意してください（取得日時など）。

---

もし README に追記したい具体的な運用手順（cron / systemd サービス定義、デプロイ方法、Dockerfile、CI 設定など）があれば、使い方 / サンプル構成を追加で作成します。