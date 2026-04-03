# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォーム・リサーチ・戦略実行の基盤ライブラリです。
DuckDB ベースのデータレイク、J-Quants API 経由の ETL、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（発注・約定トレース）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス対策（target_date を明示／内部で現在時刻に依存しない）
- DuckDB を中心とした軽量なデータ管理
- API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- ETL / 品質チェック / 監査ログを想定した堅牢な設計

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務諸表、JPX カレンダーを差分取得（ページネーション対応）
  - ETL パイプライン（差分取得・保存・品質チェック）
- データ品質（quality）
  - 欠損、スパイク、重複、日付整合性チェック
- ニュース収集・NLP
  - RSS 取得（SSRF 対策、トラッキング除去）、raw_news 保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores へ書込）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM 結合）
- 研究ユーティリティ（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査スキーマ初期化
  - 発注フローの完全なトレーサビリティを確保
- ユーティリティ
  - 設定管理（.env / .env.local の自動読み込み、環境変数保護）
  - 統計ユーティリティ（Zスコア正規化 等）

---

## 必要条件 / 依存パッケージ（代表例）

実行環境に応じて追加が必要な場合があります。最低限の代表パッケージ例：

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （ネットワークアクセス：J-Quants API / OpenAI / RSS ソース）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発時はパッケージを編集可能モードでインストール
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## 環境変数 / 設定

プロジェクトは .env（および .env.local）をプロジェクトルートから自動で読み込みます（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須/任意の環境変数：

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能使用時）
- OPENAI_API_KEY: OpenAI 呼出しを行う場合（news_nlp / regime_detector）

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: 開発/ペーパー/ライブ（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env のパースはシェル風の記法（export を許可、クォートやコメント処理に対応）に対応しています。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作成して依存をインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
pip install -e .
```

3. .env を作成（.env.example を参考に必須キーを設定）
例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB（ファイル）やデータ用ディレクトリを作成（必要なら）
```bash
mkdir -p data
```

---

## 使い方（主要ユースケースの例）

以下は Python REPL やスクリプトから呼び出す簡単な例です。DuckDB 接続は `duckdb.connect(path)` を使用します。

- ETL（日次パイプライン）を実行する：
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出（OpenAI API キーが必要）：
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))
print("wrote scores:", n_written)
```

- 市場レジームをスコアリング：
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマを初期化（監査専用 DB）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# conn を使って audit テーブルにデータを挿入できます
```

- 設定参照（コード内）：
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

注意点：
- AI 関連の関数（score_news, score_regime）は OpenAI API を呼び出します。`OPENAI_API_KEY` を環境変数に設定するか、関数の `api_key` 引数で渡してください。
- J-Quants API を呼ぶ ETL は `JQUANTS_REFRESH_TOKEN` が必要です。
- 多くの関数はルックアヘッドバイアスを避けるため `target_date` を明示的に受け取ります。内部的に date.today() を参照しない設計です（ただし pipeline.run_daily_etl の省略時は今日を使用します）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS フィード収集（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（schema 初期化 / init_audit_db）
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

各モジュールは DuckDB 接続オブジェクトを引数に取り、DB 内のテーブル（raw_prices, raw_financials, raw_news, ai_scores, market_calendar, etc.）を参照/更新します。

---

## ログ / 監視 / 運用メモ

- 設定 `LOG_LEVEL` でログ出力の詳細度を調整できます。
- ETL の結果は ETLResult（辞書化可能）で返り、品質チェックの結果を含みます。
- news_collector は RSS 取り込み時に SSRF 対策、受信サイズ制限、トラッキング除去を実施します。
- OpenAI 呼び出しにはリトライとフォールバック（失敗時はスコア 0.0）が組み込まれています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## テスト / 開発上のヒント

- AI 呼び出し部分や外部 API 呼び出しは各モジュール内でラップされているため、ユニットテストでは該当関数をモックして差し替えてテストできます（例: news_nlp._call_openai_api / regime_detector._call_openai_api / data.jquants_client._request 等）。
- DuckDB はインメモリ（":memory:"）で起動できるため、テスト用 DB の作成が容易です。
- データベーススキーマ定義（audit.init_audit_schema 等）は冪等に作成する設計です。

---

## 参考 / 連絡先

この README はリポジトリ内のソースコード（config, data, ai, research モジュール）に基づいて作成しています。実行やデプロイ時の具体的な API キー・ネットワーク構成・証券会社接続は運用ポリシーに従って取り扱ってください。

ご不明点や追加したいサンプル（CLI、Docker 化、CI ワークフロー等）があれば教えてください。README を拡張して運用手順や例を追加します。