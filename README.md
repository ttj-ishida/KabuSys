# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群（KabuSys）。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、監視設定などを含むモジュール群です。

主な設計方針
- ルックアヘッドバイアス防止（内部で date.today() 等を不用意に参照しない）
- DuckDB を中心としたローカルデータストア（冪等保存、ON CONFLICT）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- テストしやすいように API キー注入や関数差し替えが可能

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務（四半期）データ、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）を実装
  - ETL の総合実行エントリポイント `run_daily_etl`

- ニュース収集・NLP
  - RSS からのニュース収集（URL 正規化、SSRF 対策、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント計算（銘柄別 ai_scores への保存）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200乖離 と LLM 出力の重み付け合成）

- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB SQL + Python）
  - 将来リターン、IC（情報係数）、統計サマリー、Z スコア正規化

- カレンダー管理
  - market_calendar の更新ジョブ、営業日 / SQ 判定、前後の営業日取得ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを含む監査スキーマ生成
  - 監査ログ初期化ユーティリティ（`init_audit_schema` / `init_audit_db`）

- 設定管理
  - .env/.env.local または環境変数からの設定読み込み（自動ロード、ただし無効化可）
  - 環境ごと (development, paper_trading, live) とログレベルバリデーション

---

## 要件（主要依存）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装している箇所も多い）

実際に使用する環境では上記パッケージをインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

プロジェクト配布に requirements.txt / pyproject.toml があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン（パッケージは src/ 配下に配置）
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # （プロジェクトが pip インストール可能なら）
   pip install -e .
   ```
4. 環境変数の準備
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（`.env.local` は上書き）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（または重要）環境変数例
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_PASSWORD: kabu ステーション用パスワード（実取引時）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視等で使う SQLite パス（デフォルト data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知で使用する場合

.env の例（プロジェクト側で .env.example を参照してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトから呼ぶ例です。各例はエラー処理やログ設定を省略しているため、実運用では適切にハンドルしてください。

- DuckDB 接続の作成（デフォルトパスを settings から取得）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（J-Quants からの株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を明示すること（ルックアヘッド防止）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 AI スコア）を生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーを environment に設定しておくか、api_key 引数で与える
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（MA200 と マクロニュースの LLM 評価を合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB（監査専用 DuckDB）を初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイル名を指定
```

- RSS を取得して raw_news に保存するワークフロー（fetch_rss は単体の取得関数）
```python
from kabusys.data.news_collector import fetch_rss, preprocess_text, _make_article_id
from datetime import datetime

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 取得した articles を DB に永続化する処理はプロジェクト側で実装します
```

注意点
- OpenAI への呼び出しは内部でリトライやフェイルセーフを行いますが、API キー／料金・レート制限に注意してください。
- run_daily_etl 等は内部で date の扱い（target_date を明示）を重視しているため、バックテスト時は適切に日付を指定してください。

---

## 設定の自動読み込みについて

- `kabusys.config` モジュールは実行時にプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きします（ローカル専用の上書き設定用）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の値を参照するプロパティ（例: settings.jquants_refresh_token）は未設定時に ValueError を投げます。

.env のパース仕様の要点
- `export KEY=val` 形式に対応
- シングル/ダブルクォート内のエスケープ処理をサポート
- コメント（#）は値がクォートされていない場合、直前がスペース/タブならコメントと見なす

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）の主要モジュールです。詳細は各モジュールの docstring を参照してください。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # 銘柄別ニュースセンチメント計算
    - regime_detector.py   # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得・保存）
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult の再エクスポート
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記は抜粋です。実際のファイル一覧はリポジトリの src/kabusys を参照してください。）

---

## ロギング・監視

- `settings.log_level` でログレベルを制御します（環境変数 LOG_LEVEL）。
- 監視関連の設定（CPU/Memory/Disk 閾値、PID/KILL ファイルパス等）は settings で参照できます。
- 実行プロセス用の PID ファイルや kill フラグのパスは環境変数で上書き可能です。

---

## 開発・テスト（補足）

- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みを抑制できます。
- モジュール内の外部 API 呼び出しポイントはモック差し替え（unittest.mock.patch 等）を想定して設計されています（例: OpenAI 呼び出し関数の差し替え）。

---

## 参考・補足

- 各モジュールの docstring に設計方針・想定するデータスキーマ・失敗時の振る舞いが詳細に記載されています。実運用での安全性（レート制御、リトライ、フェイルセーフ）、およびルックアヘッドバイアス対策の理由付けが各所にあります。
- 実環境で「実際の発注（kabu ステーション等）」を統合する場合は、発注・ポジション管理・リスク制御の追加実装が必要です（本ライブラリはデータプラットフォームと分析、監査ログを中心に提供します）。

---

もし README に追加したいサンプルスクリプト（cron / systemd 用の起動例や Dockerfile、CI 設定など）があれば、目的に合わせて例を追記します。どの部分をより詳細に説明したいか教えてください。