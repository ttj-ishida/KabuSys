# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主に DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価やレジーム判定を行います。

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）
- 使い方（代表的な API 例）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株に関するデータ取得・品質チェック・特徴量計算・AI ベースのニュース解析・市場レジーム判定・監査ログを一貫して処理するためのモジュール群です。  
設計上の特徴は以下の通りです：

- Look-ahead バイアス回避を意識した日時処理（内部で datetime.today() を不用意に参照しない等）
- DuckDB を中心とした ETL / 永続化（冪等保存を考慮）
- OpenAI の JSON Mode を活用した安定した NLP 呼び出し（リトライやフォールバックを内包）
- J-Quants API 用クライアント（レート制御・トークン自動リフレッシュ・リトライ）
- ニュース収集での SSRF 対策・XML パース安全化（defusedxml）
- 監査ログ（signal / order_request / execution）により発注フローをトレース可能

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）／無効化オプションあり
  - 必須環境変数のアクセスラッパ
- データ（kabusys.data）
  - J-Quants API クライアント（fetch / save）
  - ETL パイプライン（run_daily_etl 等）
  - 市場カレンダー管理（is_trading_day, next_trading_day など）
  - ニュース収集（RSS 取得、前処理、raw_news 保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化 / DB 作成ユーティリティ
  - 汎用統計ユーティリティ（zscore 正規化）
- AI（kabusys.ai）
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- 研究用ユーティリティ（kabusys.research）
  - モメンタム／ボラティリティ／バリューなどファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
（プロジェクトの pyproject.toml / requirements を参照して適切にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそれを使用）
4. パッケージをインストール（開発モード）
   - pip install -e .
5. 環境変数を準備
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化したい場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です。プロジェクトルートに .env ファイルを作成してください。

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必要な場合）
- KABU_API_PASSWORD: kabuAPI のパスワード（kabu ステーション連携がある場合）

オプション（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）
- OPENAI_API_KEY: OpenAI 呼び出しのデフォルト API キー（score_news / score_regime で参照）

.env の例（雛形）
OPENAI_API_KEY=your_openai_key
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表例）

下記は Python インタプリタやスクリプトから呼び出す例です。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 日次 ETL 実行（DuckDB 接続が必要）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュース NLP スコアリング
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使う場合 api_key=None
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は dict のリスト [{"date":..., "code": "...", "mom_1m": ...}, ...]
```

---

## ディレクトリ構成（主要ファイルと役割）

以下は src/kabusys 配下の主要モジュールの概要です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・設定ラッパ。プロジェクトルートの .env/.env.local を自動読み込み（無効化可）。
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS 由来の raw_news を銘柄ごとに集約し OpenAI に投げて ai_scores テーブルへ書き込む。
      - リトライ・レスポンス検証・チャンク処理を実装。
    - regime_detector.py
      - ETF 1321 の 200 日 MA 乖離とニュースセンチメントを合成して日次の market_regime を計算・書き込み。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API への問い合わせ、ページネーション処理、レート制御、トークン管理、DuckDB への保存関数を提供。
    - pipeline.py
      - run_daily_etl 等、ETL の高レベル API を提供（差分取得・保存・品質チェック）。
    - quality.py
      - 欠損・重複・スパイク・日付不整合の品質チェック。
    - calendar_management.py
      - market_calendar の扱い、営業日判定・前後営業日検索。
    - news_collector.py
      - RSS フィード取得、安全対策（SSRF / size / XML）・記事正規化・raw_news 保存（未完成部分に注意）。
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL と初期化ユーティリティ。
    - etl.py
      - ETLResult の再エクスポート（pipeline の結果型）。
    - stats.py
      - zscore_normalize 等の統計ユーティリティ。
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー等の計算。
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、ランク化ユーティリティ。

---

## 注意事項 / 運用メモ

- OpenAI API 連携
  - score_news / score_regime は api_key 引数を受け取ります。None を渡すと環境変数 OPENAI_API_KEY を参照します。
  - API 呼び出しはリトライやフォールバック（スコア = 0.0）を行う設計ですが、利用量には注意してください。
- .env 自動読み込み
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を探索し .env を読み込みます。テスト時などで自動読み込みを阻止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 互換性
  - 一部処理は DuckDB の executemany に空リストを渡せない（バージョン差）ことを考慮していますが、実運用環境の DuckDB バージョンで動作確認を行ってください。
- news_collector.py
  - ファイル末尾付近に（gzip 処理など）未完の箇所があるため、RSS 周りはローカルでテスト・補完してから本番導入してください（コードを参照のこと）。
- テストとデバッグ
  - API 呼び出し部分（OpenAI / J-Quants / HTTP）には差し替え（モック）用の箇所が用意されています。ユニットテストではこれらをパッチすることで外部依存を切り離せます。

---

必要に応じて README にサンプル .env.example を追加したり、CI 用の構成・データスキーマ（DDL）や運用ランブックを別ドキュメントで整備することを推奨します。README の補足・翻訳や関数別の詳細ドキュメントが必要であれば指示してください。