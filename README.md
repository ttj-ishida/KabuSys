# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、ファクター計算、監査ログなどを含むモジュール群を提供します。

## 概要（Project overview）

KabuSys は日本株のデータ取得・品質チェック・研究（ファクター計算）・AI ベースのニュースセンチメント解析・市場レジーム判定・監査ログ管理を行うための内部ライブラリセットです。DuckDB を用いたローカルデータストアと J-Quants / OpenAI / RSS 等の外部データソースを組み合わせて、バックテスト／運用ワークフローの基盤を提供します。

主な設計方針:
- ルックアヘッドバイアス対策（内部で date.today() を安易に参照しない等）
- 冪等処理（DB への保存は ON CONFLICT を利用）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- テスト容易性を考慮した設計（API 呼び出し箇所を差し替え可能）

## 機能一覧（Features）

- データ取得／ETL
  - J-Quants から日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得（ページネーション・レート制御・自動トークンリフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損値、スパイク（前日比閾値）、重複、日付不整合（未来日付や非営業日のデータ）を検出

- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存
  - 再試行・バッチ処理（最大チャンクサイズ等）

- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定・保存

- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化ユーティリティ（DuckDB）
  - order_request_id を冪等キーとして二重発注防止を想定

## 必要条件（Requirements）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

（実際の requirements ファイルはプロジェクト側で管理してください）

## 環境変数（主要項目）

KabuSys は環境変数 / .env ファイルから設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基に .env → .env.local の順で行います。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news/regime のデフォルト）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: execution 環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

サンプル .env（.env.example としてプロジェクトに追加する想定）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（Setup）

1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクトが指定する依存をインストールしてください（requirements.txt があれば pip install -r requirements.txt）

3. パッケージをインストール（開発モード）
   - プロジェクトルートに pyproject.toml / setup.cfg 等があれば:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルの環境変数を設定します。
   - 自動ロード確認: kabusys.config が起動時に .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

## 使い方（Usage）

以下は代表的なユースケースの Python スクリプト例です。いずれも DuckDB 接続（duckdb.connect）を渡して使用します。

- 日次 ETL 実行（株価 / 財務 / カレンダー 取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアリング（ai_scores に書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境にあれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（market_regime に書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
# ファイル DB を作成してテーブルを初期化
conn = init_audit_db("data/audit.duckdb")
```

- 市場カレンダーの夜間更新ジョブ（単体）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

注意点:
- OpenAI 呼び出しは API キーを環境変数 OPENAI_API_KEY または関数引数 api_key で与えます。
- J-Quants の API 認証は JQUANTS_REFRESH_TOKEN を設定するか、get_id_token の引数を利用します。
- DuckDB のスキーマ（raw_prices, raw_news, ai_scores, market_regime 等）はプロジェクト側で事前に用意しておく必要があります（ETL / schema 初期化機能を提供する場合があります）。

## 自動 .env ロード仕様

- プロジェクトルート（.git または pyproject.toml を親階層に持つディレクトリ）を探索して、見つかった場合はプロジェクトルートの `.env` → `.env.local` を読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル形式に寄せた実装で、export プレフィックスやクォート、行末コメント等に対応しています。

## ディレクトリ構成（Directory structure）

以下は主要モジュールの抜粋構成です（src/kabusys 配下）。実際のファイル数はプロジェクトによって差があります。

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NLP（OpenAI）と ai_scores 書き込み
    - regime_detector.py           - 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - etl.py                       - ETL 結果型の再エクスポート（ETLResult）
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore 正規化等）
    - calendar_management.py       - マーケットカレンダー管理（営業日判定等）
    - news_collector.py            - RSS ニュース収集
    - audit.py                     - 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py           - ファクター計算（momentum/value/volatility）
    - feature_exploration.py       - 将来リターン・IC・統計サマリー等

## ログと実行環境

- ログレベルは環境変数 LOG_LEVEL（デフォルト INFO）で制御します。
- KABUSYS_ENV により実行モード（development / paper_trading / live）を切り替えられます。live モードでは本番運用における追加制約や安全チェックを想定しています（コード内で参照）。

## テスト・モック

- OpenAI、J-Quants、RSS 取得等の外部呼び出し箇所はテスト時にモック差し替えがしやすい実装になっています（内部の呼び出し関数を patch する等）。
- DuckDB は ":memory:" でインメモリ DB を利用できます（テスト用に便利）。

---

この README はコードベースの要点をまとめたものです。実際の運用・展開にあたってはプロジェクトルートの pyproject.toml / docs / examples / scripts 等を参照し、必要なスキーマ初期化・マイグレーション・運用手順を整備してください。必要があれば README にサンプル SQL スキーマや運用スクリプトの記載も追加します。