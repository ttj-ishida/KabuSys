# KabuSys

KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買補助のための Python ライブラリ群です。J-Quants API からのデータ収集（ETL）、ニュース収集と LLM による記事センチメント解析、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ用スキーマなどを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を安易に使わない）
- DuckDB をデータストアとして使用し、ETL は冪等に設計
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／マクロ判定をバッチ処理で実行
- J-Quants API 用の堅牢なリクエスト・リトライ・レート制御実装

---

## 機能一覧

- データ取得 / ETL（kabusys.data.pipeline）
  - 日次 ETL（株価、財務、カレンダー）
  - 差分更新 / バックフィル対応
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、安全対策（SSRF/プライベートアドレス検証、サイズ制限）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成
  - raw_news / news_symbols への保存ロジックを想定

- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウの記事を銘柄ごとにまとめ、OpenAI により銘柄別センチメントを JSON で取得
  - バッチ送信、リトライ、レスポンスバリデーション、ai_scores への書き込み

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200日 MA 乖離（70%）とマクロニュース LLM スコア（30%）を合成して
    daily market_regime を判定（bull / neutral / bear）

- 研究（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ、Zスコア正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化可能

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 環境変数のバリデーション、settings オブジェクトを通じたアクセス
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 前提 / 必須環境変数

必須（使用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client が必要）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合

オプション（デフォルト値あり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

注意: .env.example はリポジトリに用意する想定です（このコードベースには含まれていません）。.env をプロジェクトルートに置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化すると自動ロードは無効）。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. Python バージョン
   - Python >= 3.10 を推奨（型アノテーションに | を使用しているため）

3. 必要パッケージのインストール（最小）
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt を用意している場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 例 (.env):
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   .env は自動的に読み込まれ、.env.local がある場合はそちらが優先されます。

5. DuckDB ファイルディレクトリの準備（必要に応じて）
   - デフォルトは data/kabusys.duckdb
   - 必要であればディレクトリを作成: mkdir -p data

---

## 使い方（主要なユースケース例）

下記は Python REPL 例です。duckdb を使って接続し、各機能を呼び出せます。

- DuckDB に接続する
```python
import duckdb
conn = duckdb.connect('data/kabusys.duckdb')
```

- 日次 ETL を実行する（J-Quants の ID トークンを settings から取得して実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を作成
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# OpenAI API キーは環境変数 OPENAI_API_KEY を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定を実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

- 監査ログ用 DB を初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# signal_events, order_requests, executions テーブルが作成されます
```

- 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は list[dict] 形式で返る
```

備考:
- OpenAI を呼ぶ関数は引数 api_key を受け取る場合があります（テスト・上書き用）。省略時は環境変数 OPENAI_API_KEY が使われます。
- ETL / 保存系関数は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）が前提です。リポジトリにスキーマ初期化コードがある場合は先に実行してください（audit.init_audit_schema は提供済み）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュール構成（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント生成（OpenAI）
    - regime_detector.py            — マーケットレジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS ベースのニュース収集（SSRF 等に対策）
    - calendar_management.py        — マーケットカレンダー判定 / calendar_update_job
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック（missing/spike/duplicates/date）
    - audit.py                      — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - ai, data, research 以下にテストで差し替え可能な内部呼び出しポイントやモック対象関数あり

---

## 実装上の留意点 / 開発者向けメモ

- ルックアヘッドバイアス防止:
  - 多くのモジュールが target_date を明示的に受け取り、内部で datetime.today() を参照しないよう設計されています。バッチ・バックテストでの使用に最適化されています。

- 環境変数自動読み込み:
  - kabusys.config はパッケージインポート時にプロジェクトルートを探索して .env / .env.local を自動読み込みします。テストで自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- API エラーハンドリング:
  - OpenAI への呼び出しや J-Quants API 呼び出しは、レートリミット / 一時エラー / 5xx 等に対してリトライ実装が入っています。一部の関数は API 失敗時にフェイルセーフのデフォルト値（例: macro_sentiment=0.0）を使用して継続する設計です。

- DB 書き込みの冪等性:
  - jquants_client の save_* 関数や audit.init などは ON CONFLICT を使った冪等保存を行います。部分失敗に備えて run_daily_etl では段階ごとにエラーを捕捉して他処理を継続します。

- テスト容易性:
  - OpenAI 呼び出しや HTTP 接続などはモジュール内で差し替え可能なヘルパー関数に分けられており、unittest.mock.patch によるモックが容易です。

---

## さらに読む / 今後の実装予定（想定）

- execution（ブローカーへの発注・約定ハンドリング）モジュールの具体実装
- CI 向けの requirements.txt / dev-requirements.txt、およびサンプル .env.example
- スキーマ初期化スクリプト（raw_* テーブル定義）や duckdb の migration ツール
- Slack・監視向けの運用スクリプトやジョブスケジューラ連携例

---

もし README に追加したい具体的な使用例（スクリプト、Docker、CI 設定、サンプル .env）があれば教えてください。必要に応じて README を拡張します。