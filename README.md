# KabuSys

日本株向けのデータパイプライン / 研究 / AI支援市場分析 / 監査ログを備えた自動売買基盤のライブラリ群です。DuckDB をデータ層に用い、J-Quants API からのデータ取得、RSS ニュース収集・LLM によるニュースセンチメント、ETF とマクロ情報を組み合わせた市場レジーム判定、ETL パイプライン、データ品質チェック、監査テーブルの初期化などを提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐ（内部処理で date.today()/datetime.today() を無作為に参照しない）
- DuckDB を前提とした SQL + Python 実装
- 冪等性（ON CONFLICT / DELETE→INSERT など）を重視
- 外部 API 呼び出しにはリトライ・バックオフ・フェイルセーフを実装
- セキュリティ対策（RSS の SSRF 対策、defusedxml、URL 正規化等）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数のアクセスラッパー（kabusys.config.settings）

- データ収集 / ETL（kabusys.data）
  - J-Quants API クライアント（株価、財務、カレンダー等）と保存（jquants_client）
  - ETL パイプライン（run_daily_etl を含む）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS フィード、正規化、SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログDB / テーブル初期化（init_audit_db / init_audit_schema）

- AI（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコアリング（score_news）
  - マクロ + ETF MA200 を用いた市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で利用、リトライ＆フェイルセーフ実装

- 研究ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー、Zスコア正規化等

- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - データベース操作ユーティリティ（DuckDB 向け）

---

## 必要な環境・依存関係（例）

- Python 3.10 以上（型注釈に PEP 604 の `X | Y` を使用）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - requests（コード内では urllib を使用していますが、運用で使う場合に便利）
  - その他：typing-extensions（環境によって）

インストール例（pip 仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 必要に応じてプロジェクトを編集可能インストール:
# pip install -e .
```

---

## 環境変数（必須 / 任意）

主要な環境変数は `kabusys.config.Settings` で参照されます。最低限必要な値はプロジェクトの利用用途に依存しますが、AI / J-Quants を使う場合は以下が必要です。

必須（少なくとも用途に合わせて用意する）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token に利用）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用（システム全体で Slack を使う場合）
- SLACK_CHANNEL_ID — Slack の通知対象チャンネル ID
- KABU_API_PASSWORD — kabuステーションAPI のパスワード（発注等を行う場合）

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

自動ロードについて:
- パッケージの `kabusys.config` は、.git または pyproject.toml をプロジェクトルートとして探索し、プロジェクトルートの `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例（.env）:
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # あれば
# あるいは最低限:
pip install duckdb openai defusedxml
```

2. 環境変数を設定
- プロジェクトルートに `.env`（および開発用に `.env.local`）を作成し、上記の必須値を設定します。
- 自動ロードを使いたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

3. DuckDB の初期化（監査テーブルが必要な場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# またはインメモリ:
conn = init_audit_db(":memory:")
```

4. 必要に応じて監査スキーマを既存接続に適用:
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要ユースケース）

以降は Python スクリプトや REPL から呼び出す想定です。DuckDB 接続（duckdb.connect）を渡して各操作を行います。

- 日次 ETL の実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付け（OpenAI API を利用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# APIキーは環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（別 DB ファイルを監査専用に用意）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を監査ログへの書き込みに用いる
```

- ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- データ品質チェックを一覧で実行
```python
from kabusys.data.quality import run_all_checks
checks = run_all_checks(conn, target_date=None, reference_date=None)
for issue in checks:
    print(issue.check_name, issue.severity, issue.detail)
```

注意点
- score_news / score_regime は OpenAI API を呼び出します。API キーは `OPENAI_API_KEY` に設定するか、各関数の `api_key` 引数で渡してください。
- J-Quants へのアクセスは `JQUANTS_REFRESH_TOKEN` を使って ID トークンを取得します。
- DuckDB への書き込みは各関数が担当。運用ではバックアップやファイルのロック管理に注意してください。

---

## ディレクトリ構成

主要なファイル・パッケージ構成（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py      — マクロ + ETF MA を用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - pipeline.py             — ETL パイプライン / run_daily_etl
    - etl.py                  — ETLResult 再エクスポート
    - calendar_management.py  — 市場カレンダー判定・更新ロジック
    - news_collector.py       — RSS 収集・正規化・保存ロジック
    - quality.py              — データ品質チェック群
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査テーブル定義・初期化 utilities
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（Momentum, Value, Volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (パッケージ列挙済みだが詳細実装はここに)
  - execution/ (発注 / 実行ロジック: 監査連携を行う想定)
  - strategy/ (戦略定義層)

各モジュールは README の説明やドキュメント（DataPlatform.md / StrategyModel.md 等）を想定して設計されています。

---

## 開発上のヒント / 注意事項

- テスト時は外部 API 呼び出しをモックすることが推奨されます（kabusys.ai.news_nlp._call_openai_api などを patch 可能）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所では空チェックが行われています。運用時の DuckDB バージョンに注意してください。
- RSS 取得では SSRF 対策・レスポンスサイズ制限が実装されています。外部ソースを追加する際は安全性に留意してください。
- 監査テーブルは削除を想定せず、トレース可能性を重視して設計されています（ON DELETE RESTRICT 等）。

---

もし README に含めたい追加の動作例や CI / デプロイ手順、実行スクリプト（cron / systemd / Docker）などがあれば教えてください。それに合わせてサンプルやコマンド例、.env.example のテンプレートを追加できます。