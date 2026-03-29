# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群。  
DuckDB を中心としたデータETL、ニュース収集とAIによるニュース解析、ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを含むモジュール群です。

## プロジェクト概要
KabuSys は、日本株投資戦略（研究→シグナル生成→発注）を支える以下の機能群を提供します。

- データプラットフォーム（J-Quants からの株価・財務・カレンダー取得、ETL、品質チェック）
- ニュース収集・前処理・銘柄紐付け（RSS ベース）
- ニュースの LLM（OpenAI）を用いたセンチメント解析（銘柄別スコア / マクロセンチメント）
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン計算、IC 計算、正規化等）
- 監査ログ（シグナル → 発注 → 約定の追跡用スキーマ初期化）
- J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ）
- カレンダー管理（営業日判定・前後営業日の取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の共通方針として、バックテスト時のルックアヘッドバイアスを避けるため「現在時刻」を直接参照しない実装や、外部APIの失敗時に安全側で継続するフェイルセーフ性が取り入れられています。

---

## 主な機能一覧（抜粋）
- data:
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（日足・財務・カレンダー）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - ニュース収集: fetch_rss / preprocessing / 紐付けロジック
  - 品質チェック: check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
  - 監査ログ: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF とマクロニュースを合成して daily market_regime を作成
- research:
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - Settings クラスで環境変数を集中管理

---

## セットアップ手順（ローカル開発向け）

1. Python 環境準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. パッケージのインストール
   - このリポジトリを pip editable install する想定:
   ```
   pip install -e .
   ```
   （requirements.txt / pyproject.toml に依存関係を記載している想定です。OpenAI SDK、duckdb 等が必要です。）

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL に必須）
     - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（監視/通知を使う場合）
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系）
     - OPENAI_API_KEY: OpenAI API キー（AI スコアリングを有効にする場合）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化（監査ログ等）
   - 監査用 DB を初期化する簡単な例:
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")
   ```
   - または、既存の DuckDB 接続にスキーマを追加:
   ```python
   import duckdb
   from kabusys.data import audit
   conn = duckdb.connect("data/kabusys.duckdb")
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的なコード例）

- DuckDB 接続を作る:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）を実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコアリングして ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジームを判定して market_regime に保存:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクターを計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- RSS 取得（ニュース収集）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants から日足をフェッチして保存:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
```

---

## 環境変数一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (AI 機能利用時必須): OpenAI API キー
- KABU_API_PASSWORD (必須): kabu API パスワード（発注系）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py            — 市場レジーム判定（ETF MA + マクロ）
- data/
  - __init__.py
  - calendar_management.py        — 市場カレンダー管理（営業日判定等）
  - etl.py                        — ETL インターフェース再エクスポート
  - pipeline.py                   — 日次 ETL パイプライン実装
  - stats.py                      — 統計ユーティリティ（zscore 等）
  - quality.py                    — データ品質チェック
  - audit.py                      — 監査ログスキーマ作成 / init
  - jquants_client.py             — J-Quants API クライアント + 保存関数
  - news_collector.py             — RSS ニュース収集 / 前処理
- research/
  - __init__.py
  - factor_research.py            — Momentum / Value / Volatility 等
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー

その他（想定）:
- execution/                        — 発注実装（kabu ステーション連携）を想定
- monitoring/                       — 監視・アラート機能を想定

（実装済みモジュールは上記の通り。将来的に strategy/execution/monitoring の実装が追加される想定です。）

---

## 開発・テスト時の注意点
- DuckDB のバージョン差異での SQL 挙動に注意（特に executemany の空リスト、配列バインドの挙動など）。
- AI（OpenAI）呼び出しはネットワークに依存するため、ユニットテストでは _call_openai_api をモックすること。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に検索します。パッケージ配布後のテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。
- ETL 実行は外部 API と DB が前提のため、本番データを扱う際はバックアップ・監査を行ってください。
- 設計上、run_daily_etl 等は内部で date.today() を適切に使用（ルックアヘッドを避けるためターゲット日を明示して呼ぶことが推奨されます）。

---

この README はコードベースの概要と使い方を簡潔にまとめたものです。詳細な API ドキュメントや実行スクリプト、運用手順は別途補完してください。必要であれば README に含めるサンプルスクリプトやさらに細かい環境構築手順（CI/CD、cron ジョブ設定など）も作成します。どの内容を追加しましょうか？