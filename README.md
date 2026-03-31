# KabuSys

日本株自動売買プラットフォーム用のライブラリ群。データ ETL、ニュース NLP（LLM を使ったセンチメント解析）、市場レジーム判定、ファクター計算、監査ログなどの共通ユーティリティを提供します。

主な用途
- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI による銘柄別センチメント付与（AI スコア）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（momentum, value, volatility）および研究用ユーティリティ
- 監査ログテーブル（signal/order/execution）構築と初期化

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch/save の全機能、認証トークン管理、レートリミット、リトライ）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - 監査ログ（監査用テーブル DDL、インデックス、init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: 指定日のニュースを OpenAI で解析し ai_scores を更新
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM スコアを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - kabusys.config.Settings: .env 自動読み込み（プロジェクトルート判定）＋環境変数アクセスラッパー

---

## 前提・要件

- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パース安全化）
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- 環境変数（以下参照）と API トークン

（プロジェクトに requirements.txt / pyproject.toml がある想定で、そこから依存をインストールしてください）

例:
```bash
python -m pip install -r requirements.txt
# または
python -m pip install duckdb openai defusedxml
```

---

## 環境変数

以下の環境変数を設定してください。パッケージはプロジェクトルート（.git または pyproject.toml を検出）から `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション（注文 API）用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行 PID ファイル（default: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールは引数で上書き可）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```

   requirements.txt が無い場合は以下の最低限をインストールしてください:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env` / `.env.local` を配置するか、環境変数をエクスポートしてください（上記参照）。

5. DuckDB データベースのディレクトリ作成
   `.env` で `DUCKDB_PATH` を指定している場合、その親ディレクトリがなければ作成してください。多くの初期化関数は自動でディレクトリを作成しますが、念のため。

---

## 使い方（主要な操作例）

以下はライブラリを直接インポートして利用する簡単な例です。DuckDB 接続は duckdb.connect(...) を使って渡します。

- DuckDB 接続作成（デフォルト .env の DUCKDB_PATH を利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（J-Quants からデータ取得して保存・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア付与
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

dm = calc_momentum(conn, date(2026,3,20))
dv = calc_value(conn, date(2026,3,20))
dv2 = calc_volatility(conn, date(2026,3,20))
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.jquants_refresh_token)
```

注意事項:
- ai モジュール（news_nlp, regime_detector）は OpenAI API を呼び出します。テスト時は内部の _call_openai_api をモックする設計になっています。
- 多くの関数は Look-ahead バイアスを防ぐために date 引数を明示的に受け取ります（内部で datetime.today() を直接参照しない設計）。

---

## 自動 .env 読み込みについて

kabusys.config モジュールはパッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を自動読み込みします。OS 環境変数が優先され、`.env.local` は上書き（override=True）されます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル形式（export KEY=val, quoted values, inline comments）をサポートします。

---

## ディレクトリ構成

主要モジュールのファイル位置（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング
    - regime_detector.py     -- 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            -- ETL パイプライン、run_daily_etl 等
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - news_collector.py      -- RSS 収集・前処理（SSRF 対策）
    - quality.py             -- データ品質チェック
    - calendar_management.py -- カレンダー管理（営業日判定等）
    - audit.py               -- 監査ログ DDL / 初期化
    - etl.py                 -- ETLResult の再エクスポート
    - stats.py               -- 統計ユーティリティ (zscore_normalize)
  - research/
    - __init__.py
    - factor_research.py     -- momentum/value/volatility の計算
    - feature_exploration.py -- forward returns / IC / summary / rank
  - ai, data, research の各サブモジュールは __all__ を整備

---

## テスト・モック化について

- OpenAI 呼び出しは内部で _call_openai_api を通して実施されており、unit tests では patch により差し替えることで外部 API を呼ばずに検証できます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=...)
  - 同様に regime_detector でも _call_openai_api をパッチ可能
- news_collector の _urlopen もテスト向けに差し替え可能です。

---

## 開発・貢献

バグ報告や機能提案は Issue を立ててください。開発に参加する場合はブランチを切って Pull Request を送ってください。コーディング規約やテスト方針は別途 CONTRIBUTING.md に記載することを推奨します（現状未付属）。

---

## 免責事項

このライブラリは金融データの取得・解析を支援するユーティリティ群を提供しますが、自動売買の実行・資金管理は利用者の責任で行ってください。本ソフトウェアの利用により発生した損害について作者は一切の責任を負いません。

---

必要であれば README に以下を追加します（要望してください）:
- 具体的な .env.example ファイル
- requirements.txt の推奨内容
- CI / テスト実行手順
- 具体的なデータベーススキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime などの CREATE TABLE）