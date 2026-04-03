# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants、kabuステーション、OpenAI 等の外部サービスと連携して、データ取得（ETL）、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ（ファクター計算）、監査ログ（トレース可能な発注/約定履歴）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不随に使わない）
- DuckDB を用いたローカル分析データベース
- 冪等性（ON CONFLICT / トランザクション）を重視した ETL / 保存ロジック
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを考慮

---

## 主な機能一覧

- data（ETL / データ品質 / カレンダー / J-Quants クライアント）
  - run_daily_etl: 日次 ETL（市場カレンダー / 株価日足 / 財務）
  - jquants_client: J-Quants API からの差分取得・保存（rate limiting・トークン自動更新）
  - quality: 欠損・スパイク・重複・日付整合性チェック
  - news_collector: RSS ベースのニュース収集（SSRF 対策、ID生成・正規化）
  - audit: 発注／約定の監査ログ初期化ユーティリティ（監査テーブル作成）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ

- ai（ニュース NLP / レジーム判定）
  - score_news: raw_news → ai_scores へ銘柄ごとの NLP スコアを書き込み（OpenAI）
  - score_regime: ETF（1321）200日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime を書き込み

- research（ファクター計算・特徴量探索）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）

- 設定管理
  - config.Settings: 環境変数 / .env の読み込み・検証、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

---

## 要件（推奨）

- Python 3.8+
- DuckDB（Python パッケージ）
- openai（OpenAI Python SDK、gpt-4o-mini を利用）
- defusedxml（RSS パースの安全化）
- その他標準ライブラリ（urllib 等）

インストール例（最低限の依存）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカルで使う場合:
pip install -e .
```

※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

---

## 環境変数（主要）

以下の環境変数がコード内で参照されます。`.env` / `.env.local` をプロジェクトルートに置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（約定連携等）

任意（機能に応じて）:
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | ...)

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の自動読み込みについて:
- プロジェクトルートは `pyproject.toml` または `.git` を起点に自動検出され、`.env` と `.env.local` を読み込みます。
- 読み込み優先は OS 環境 > .env.local > .env です。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに pyproject/requirements があればそれを使う
   pip install -e .
   ```

4. 環境変数を準備（.env をプロジェクトルートに作成）
   - .env.example を参考に JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY（必要な場合）等を設定

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単なコード例）

以下はライブラリ内の公開関数を使った基本例です。すべて Python スクリプトや REPL から実行できます。

- DuckDB 接続の準備（デフォルトパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を走らせる
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは環境変数 OPENAI_API_KEY か、api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB の初期化（独立 DB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は自動で呼ばれる
```

- 研究用ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点：
- score_news / score_regime は OpenAI を呼ぶため API キーと利用上の注意（費用）があります。
- run_daily_etl は J-Quants API に対する認証トークン取得を行うため、JQUANTS_REFRESH_TOKEN の設定が必要です。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル／モジュールは以下のような構成です（src 以下を示しています）。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存
    - pipeline.py            # ETL（run_daily_etl など）
    - etl.py                 # ETLResult の再エクスポート
    - quality.py             # 品質チェック
    - news_collector.py      # RSS ニュース収集
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - stats.py               # 統計ユーティリティ（zscore_normalize 等）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum/Value/Volatility 等の計算
    - feature_exploration.py # 将来リターン / IC / summary
  - research/ 以下のユーティリティ群

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、DB 層（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar, など）を参照・更新する設計です。

---

## 設計上の重要な注意点

- Look-ahead-bias に配慮：多くの関数で target_date を引数に取り内部で現在時刻を用いない実装を採用しています（バックテスト等での安全性確保）。
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフで堅牢化されています。API エラー時は必要に応じてスキップして処理を継続することがあるため、戻り値やログを確認してください。
- DuckDB に対する executemany/INSERT は一部バージョン差異があるためコード内で互換性処理が施されています。

---

## 開発・テスト

- 単体テストでは外部 API 呼び出しをモックする設計（例: news_nlp._call_openai_api の差し替え）になっています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、自動で .env をロードしないようにできます。
- DB を使ったテストでは ":memory:" の DuckDB 接続を利用できます。

---

必要に応じて README を拡張して、CI/CD 実行手順、スケジューリング（cron / systemd / kubernetes CronJob）や運用監視、ロギング設定、より詳細な schema 定義・SQL スキーマ初期化手順などを追加できます。用途（バックテスト・ポートフォリオ運用・データ収集）に合わせて利用・拡張してください。