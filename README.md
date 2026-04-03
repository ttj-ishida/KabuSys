# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API による市場データ取得・ETL、ニュース収集・NLP スコアリング（OpenAI）、ファクター計算・リサーチ、監査ログ／発注トレーサビリティ、マーケットカレンダー管理などを提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を中心とした冪等なデータ保存」「外部 API 呼び出しの堅牢化（リトライ・レート制御）」「モジュール間の疎結合」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - settings オブジェクトでアプリ設定を取得（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, DUCKDB_PATH）

- データ ETL（jquants_client + pipeline）
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存
  - rate limiting / リトライ / トークン自動リフレッシュ対応
  - ETL の結果を表す ETLResult（品質チェック結果含む）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出するチェック群（quality モジュール）

- ニュース収集・前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、本文前処理）
  - raw_news への冪等保存と銘柄紐付け

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に送信し ai_scores を生成（JSON Mode、バッチ処理・リトライ制御）
  - マクロニュースのセンチメント評価＋ETF MA 乖離を合成して市場レジームを判定

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Z スコア正規化ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - 発注フローのトレーサビリティ（UUID による冪等性）

---

## セットアップ手順

ここではローカル開発環境での基本的な手順を示します。プロジェクトに pyproject.toml / requirements.txt がある前提で進めてください（なければ下記の依存を手動でインストールしてください）。

1. Python（推奨: 3.10 以上）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e . などでローカルパッケージとしてインストール
4. 環境変数を用意
   - プロジェクトルートに `.env` として次の変数を設定（例を参照）
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例: .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- settings オブジェクトは必須変数が未設定だと ValueError を raise します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必須のプロパティで参照される箇所がある）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点とします。

---

## 使い方（簡単な例）

以下は主要なユースケースの簡単な使用例です。実際の運用ではログ設定や例外処理を適切に行ってください。

1) 設定参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

2) DuckDB 接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETLResult の内容を辞書化して確認
```

3) ニュースを LLM でスコアリングして ai_scores に保存
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai scores")
```

4) 市場レジーム判定（ETF 1321 の MA200 乖離＋マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5) リサーチ系ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

6) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

# ディスク上の DuckDB ファイルを作成して監査スキーマを初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 重要な設定・環境変数

主な環境変数（settings 経由で参照されるもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化

settings オブジェクトはプロパティを通して値を取得します。必須値が未設定の場合は ValueError が出ます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py            — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースNLP（銘柄別スコアリング）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得＆保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - quality.py          — データ品質チェック
    - news_collector.py   — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py — マーケットカレンダー管理
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai/他、research などのテスト対象モジュール

（上記はメインモジュールのみ抜粋。詳細はソース参照）

---

## トラブルシューティング / 注意点

- 環境変数が足りないと settings のアクセス時に ValueError が発生します。まず .env を準備してください。
- OpenAI・J-Quants の API 呼び出しは外部サービス依存のため、APIキーやネットワーク設定を確認してください。
- news_nlp / regime_detector は OpenAI を使います。API レート・コストに注意してください。失敗時はフェイルセーフ（スコア 0.0 等）で動作する設計です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンの注意点に対応した実装がありますが、古い環境で問題が出る場合は DuckDB のバージョンを確認してください。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から探索します。ユニットテスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発・テスト

- 単体テストや CI を行う場合は、環境変数の注入を明示的に行うか、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してからテスト用の .env をロードするフローを整えると良いです。
- LLM 呼び出しを含む関数は `_call_openai_api` の差し替え（モック）を想定した設計になっています。ユニットテストでは該当関数をパッチして API 呼び出しを模擬してください。

---

README は以上です。実装の詳細や API の利用方法は各モジュール（src/kabusys/data/*.py、src/kabusys/ai/*.py、src/kabusys/research/*.py）内の docstring を参照してください。必要であれば README にサンプル .env.example や詳細な実行スクリプト例、開発フロー（pre-commit, lint, tests）を追加できます。