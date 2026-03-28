# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータ基盤＆自動売買リサーチ基盤です。J-Quants / RSS / kabuステーション / OpenAI など外部データを取り込み、ETL → 品質チェック → ファクター計算 → ニュースセンチメント評価 → 市場レジーム判定 → 監査ログ（発注→約定トレース）までをサポートします。

主目的は、安全で再現可能なデータパイプラインと研究ワークフロー（バックテストや運用に利用可能な指標）を提供することです。

---

## 主な機能

- ETL パイプライン（jquants からの株価 / 財務 / カレンダー取得）
- DuckDB への冪等保存（ON CONFLICT / UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（営業日判定、next/prev trading day 等）
- RSS ニュース取得・前処理（SSRF対策、トラッキング除去）
- ニュースの LLM（OpenAI）による銘柄別センチメント集約（ai_scores 書込み）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- リサーチ用ファクター計算（モメンタム／ボラティリティ／バリュー 等）
- 統計ユーティリティ（Zスコア正規化、IC・前方リターン算出）
- 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

設計上の注目点:
- Look-ahead バイアス回避（関数は target_date を引数に取り date.today() を直接参照しない）
- API 呼び出しの冗長性に対するフェイルセーフ（API失敗時はスキップ/フォールバック）
- 冪等性（DB 書込みは重複上書きや ON CONFLICT を利用）
- J-Quants API のレート制御・再試行ロジック内蔵

---

## 要求環境 / 依存ライブラリ

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等を利用

インストール例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# パッケージをローカル編集可能インストールする場合（プロジェクトルートで）
python -m pip install -e .
```

（プロジェクト配布に requirements.txt がある場合はそちらを参照してください）

---

## 環境変数（主な必須項目）

アプリケーション設定は .env / .env.local または OS 環境変数からロードされます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しで使用する API キー（score_news / score_regime 実行時に必要）

オプション（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -e .
   pip install duckdb openai defusedxml
   ```

4. .env を作成（上記参照）

5. DuckDB ファイルの格納先ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python スクリプト / REPL からの利用例です。

- DuckDB 接続作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示して実行（None＝today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI を使って銘柄別スコアを ai_scores に保存）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定されているか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに regime_score / regime_label が書き込まれます
```

- 監査ログデータベース初期化:
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB、またはファイルパスを指定
audit_conn = init_audit_db("data/audit.duckdb")
```

- リサーチ関数（例: モメンタム計算）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

注意:
- AI 関連機能は OpenAI SDK を使用します。API 呼び出しの失敗は各関数で安全にフォールバック（0.0 やスキップ）される設計ですが、API キーの設定は必須です。
- 関数は target_date を受け取るため、バックテスト等での再現が容易です。date.today() を暗黙参照しない設計です。

---

## 便利な運用ポイント / 設計上の注意

- 自動環境変数ロード: パッケージインポート時にプロジェクトルート（.git または pyproject.toml の位置）を探索して .env と .env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効にできます。
- J-Quants クライアントは API レート制御とリトライを内蔵しています。大量取得はレート制限に注意してください。
- ETL / 保存処理は部分失敗に耐えられるように設計されています（品質チェックが失敗してもできる範囲で処理を継続）。
- DuckDB の executemany は空リスト渡しに制限があるため、空パラメータは呼び出し前にチェックされています（互換性考慮）。
- OpenAI 呼び出しは JSON モードを利用し、レスポンスの厳格なバリデーションを実施しています。429 やネットワークエラーは指数バックオフでリトライします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
  - パッケージのエントリポイント。__version__ を定義。

- config.py
  - 環境変数 / .env ロード、Settings クラス（各種設定取得）。

- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM センチメントスコアリング（ai_scores へ書込む）
  - regime_detector.py — ETF (1321) MA とマクロニュースを合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl 等）
  - etl.py — ETLResult の再エクスポート
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付整合）
  - calendar_management.py — マーケットカレンダー管理（is_trading_day, next_trading_day 等）
  - news_collector.py — RSS 取得 / 前処理 / 保存周り（SSRF 対策・サイズ制限）
  - audit.py — 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）

- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等

※ 上記以外にも strategy / execution / monitoring などの名前空間が想定されています（パッケージ __all__ に列挙）。

---

## 開発 / テスト時のヒント

- テストでは OpenAI クライアント／HTTP 呼び出しをモックしてください（各モジュールで _call_openai_api や _urlopen を差し替え可能に設計されています）。
- 自動 .env ロードはテスト環境の副作用を避けるため無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB を ":memory:" で使えば一時的なテスト DB を作れます（data.audit.init_audit_db(":memory:") 等）。

---

この README はコードベース（src/kabusys）から抜粋してまとめた概要です。各モジュールの詳細実装や引数仕様は該当ファイルの docstring / 型注釈を参照してください。質問や追加で載せてほしいサンプル（例: 実運用時の cron ジョブ例、Slack 通知の使い方等）があれば教えてください。