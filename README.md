# KabuSys

日本株向けのデータプラットフォーム＆自動売買基盤ライブラリ（モジュール群）。  
ETL、データ品質チェック、ニュース収集・NLP、ファクター研究、監査ログ、J-Quants / kabu API クライアント等を含む統合ツールキットです。

---

## プロジェクト概要

KabuSys は日本株投資のための内部データ基盤と研究・自動売買の基礎機能を提供する Python パッケージです。主な目的は以下：

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に蓄積する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集とニュース NLU（OpenAI を利用したセンチメント評価）
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 発注フローの監査ログ用スキーマ（監査テーブルの初期化 / 専用 DB 作成）
- J-Quants API クライアント（認証・レート制御・リトライ・DuckDB への保存）

設計上の特徴として、「ルックアヘッドバイアスを避ける」「冪等性」「フェイルセーフ（API失敗で停止しない）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_*/save_*、認証・レート制御）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - ニュース収集（RSS fetch, 前処理, raw_news への冪等保存設計）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 指定ウィンドウのニュースを LLM で銘柄別にスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュース LLM スコアを合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件・依存

- Python 3.10 以上（| 型記法や型ヒントが利用されているため）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時: pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数と設定

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし CI やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI を使う機能（score_news / score_regime 等）で使用（関数呼び出し時に引数で渡すことも可）

オプション:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

.env の例（要機密情報の管理に注意）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env`（および任意で `.env.local`）を作成して必須変数を設定
5. DuckDB データベースディレクトリを作成（例: data/）
   ```
   mkdir -p data
   ```
6. 監査ログ DB を初期化する場合:
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
   ```

---

## 使い方（主要な呼び出し例）

- DuckDB 接続準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
run_daily_etl はカレンダー → 株価 → 財務 → 品質チェック の順で実行します。各ステップは個別にエラーハンドリングされ、ETLResult に集約されます。

- ニュースのセンチメントスコア付与（ai_scores 書き込み）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```
OPENAI_API_KEY が環境変数または api_key 引数で指定されている必要があります。

- 市場レジーム判定（market_regime 書き込み）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)

# Z-score 正規化（例）
mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログスキーマ初期化（既存接続に追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 実装上の注意点 / 設計メモ

- Look-ahead bias を防止するため、内部処理は datetime.today()/date.today() を無闇に参照しない設計（多くの関数は target_date を引数で受ける）。
- J-Quants クライアントはレート制御（120 req/min）や認証リフレッシュ、リトライ（指数バックオフ）を備えています。
- OpenAI 呼び出しは JSON mode を利用し、429・タイムアウト・ネットワークエラー・5xx はリトライ、最終的にはフォールバック（0.0 等）で継続するフェイルセーフ実装です。
- DuckDB に対する保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- news_collector は SSRF 対策、XML の安全パース（defusedxml）、レスポンスサイズ制限など多数の安全対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリ内の主要モジュールファイル一覧（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記は本 README 作成時点の主要ファイルを反映しています）

---

## よくある運用フロー

- 日々のバッチ（cron / Airflow 等）で:
  - run_daily_etl を定期実行（ETL + 品質チェック）
  - news_collector を定期実行して raw_news を更新
  - score_news / score_regime を ETL 後に実行して AI スコア・レジームを更新
- 監査ログは別 DB（init_audit_db で作成）に保存して運用監査トレースを確保
- 本番切替時は KABUSYS_ENV=live を設定、paper_trading モードなどで発注ロジックを分離

---

## サポート / 開発メモ

- テストや CI で .env 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 HTTP 呼び出しはユニットテストで差し替え可能なように設計されています（モジュール内の _call_openai_api や _urlopen を patch する等）。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に注意して実装されています。

---

この README はコードベース（src/kabusys 以下）の説明に基づいて作成しました。実際の運用では secrets の安全管理、OpenAI/J-Quants レート・コスト管理、発注フローの十分な検証を行ってください。