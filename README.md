# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータパイプライン、ファクター/リサーチ、ニュース/NLP、監査ログ、ETL、そして市場レジーム判定や AI を利用したニュースセンチメント評価などを含む自動売買／研究用のライブラリ群です。本リポジトリはモジュール化され、DuckDB を用いたローカルデータベースでの ETL / 品質チェック / 監査ログ管理および J-Quants / OpenAI など外部 API と連携します。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数 (.env) と挙動
- 使い方（簡単なコード例）
  - ETL（run_daily_etl）
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - 監査ログ DB 初期化（init_audit_db）
  - カレンダー操作ユーティリティ
- ディレクトリ構成（主要ファイル説明）
- 補足 / 設計上の注意点

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python ライブラリです。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 発注〜約定までをトレース可能にする監査ログスキーマ（DuckDB）

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API の取得・保存・認証・ページネーション・レートリミット処理
  - pipeline: 日次 ETL 実行（run_daily_etl）・個別 ETL ヘルパー
  - quality: データ品質チェック群（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - news_collector: RSS フィード取得・前処理・raw_news への保存ロジック（SSRF 対策、トラッキング除去など）
  - calendar_management: JPX カレンダーの管理・営業日判定・next/prev_trading_day
  - audit: 監査ログ用テーブル作成・DB 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ

- ai:
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント生成 → ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込む

- research:
  - factor_research (calc_momentum / calc_value / calc_volatility)
  - feature_exploration (calc_forward_returns / calc_ic / factor_summary / rank)

- config:
  - 環境変数 / .env の自動読み込み・検証を行う Settings

---

## 必要条件 / 依存関係

- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリを使用（urllib, datetime, logging, json, etc.）

実行環境に応じて追加パッケージが必要になる場合があります（例: J-Quants 実利用時のネットワーク、OpenAI API キー、kabuステーション API 連携など）。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロードする

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数を設定する（下記参照）。開発時はプロジェクトルートに .env ファイルを置くと自動読み込みされます。

---

## .env / 環境変数

kabusys.config.Settings により .env（および .env.local）を自動読み込みします（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン

- kabuステーション API
  - KABU_API_PASSWORD (必須): kabu API パスワード
  - KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"

- OpenAI
  - OPENAI_API_KEY (推奨): score_news / regime_detector のデフォルト API キー

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)

- 監視 / 実行
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

- 実行モード
  - KABUSYS_ENV = development | paper_trading | live
  - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

設定が不十分な必須項目は Settings プロパティから参照した際に例外が発生します（例: JQUANTS_REFRESH_TOKEN が未設定だと ValueError）。

---

## 使い方（主要 API の例）

以下は主要ユースケースの簡単な使用例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

注意: 各関数は DuckDB 接続を受け取る設計です。実運用では接続管理（排他・トランザクション）に注意してください。

- 1) 日次 ETL を実行する（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 2) ニュースセンチメントをスコア化して ai_scores に保存する（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を渡さない場合は OPENAI_API_KEY 環境変数が使われる
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 3) 市場レジームを判定して market_regime に書き込む（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 4) 監査ログ用 DB を初期化する（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブル・インデックスが作成されます
```

- 5) カレンダー関連ユーティリティ例

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（主要ファイルと簡単な説明）

プロジェクトの主要なソースコードは `src/kabusys` 配下にあります。

- src/kabusys/__init__.py
  - パッケージ定義 / バージョン

- src/kabusys/config.py
  - Settings クラス: 環境変数管理・.env 自動読み込みロジック

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - pipeline.py: ETL のエントリポイント（run_daily_etl 等）と ETLResult
  - quality.py: データ品質チェック（各チェック関数）
  - news_collector.py: RSS 取得・前処理・SSRF 対策・raw_news 保存ロジック
  - calendar_management.py: JPX カレンダー管理・営業日ロジック・calendar_update_job
  - audit.py: 監査ログテーブル DDL と初期化ユーティリティ
  - stats.py: zscore_normalize など統計ユーティリティ
  - etl.py: pipeline.ETLResult の再エクスポート

- src/kabusys/ai/
  - news_nlp.py: ニュースをまとめて OpenAI に送り銘柄別スコアを ai_scores に保存するロジック
  - regime_detector.py: ETF MA200 乖離とマクロニュース LLM を合成して market_regime に書き込む

- src/kabusys/research/
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: forward returns, IC, factor_summary, rank
  - __init__.py: 便利な再エクスポート

- その他
  - src/kabusys/data/jquants_client.py 内に保存用ユーティリティ（save_*）と取得（fetch_*）
  - 各モジュールには Look-ahead bias 回避やフェイルセーフ、トランザクション管理等の設計が反映されています

---

## 設計上の注意・運用メモ

- Look-ahead bias 回避:
  - 日付計算は内部で date.today()/datetime.today() を直接参照しない関数設計（target_date を明示的に渡す）
  - ETL / スコア関数は target_date を引数に受け取り、バックテストでも同じ振る舞いになるよう設計されています

- エラー・フェイルセーフ:
  - OpenAI / HTTP API 呼び出しはリトライとフォールバック（例: マクロセンチメント失敗時は 0.0）を備え例外を抑制する箇所があります
  - ETL の各ステップは個別にハンドリングされ、可能な限り処理を続行する設計です

- DuckDB の executemany の動作に注意:
  - 一部関数は DuckDB のバージョン差に配慮して空リストを executemany に渡さない等の実装上の工夫があります

- .env 自動読み込み:
  - import 時点でプロジェクトルート（.git または pyproject.toml を親階層に探索）を検出し .env/.env.local を読み込みます
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

---

必要に応じて README を拡張して、セットアップ用のスクリプト例、CI 設定、運用手順（cron / systemd ユニット例）、テストの実行方法などを追加できます。追加したい項目があれば教えてください。