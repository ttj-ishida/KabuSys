# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants / RSS / OpenAI 等からデータを収集・加工し、ファクター計算・ニュースセンチメント・市場レジーム判定・ETL／品質チェック・監査ログなどの機能を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時の安全な継続）」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local から自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の明示的参照（不足時にエラー）

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場銘柄情報）
  - 差分取得／ページネーション対応／レートリミット管理／トークン自動リフレッシュ
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - データ保存（DuckDB への冪等保存）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複、日付整合性チェック
  - QualityIssue を返す設計で Fail-Fast を行わず問題を収集

- ニュース収集 / NLP
  - RSS フィードから記事収集（SSRF 対策、URL 正規化、トラッキング除去、サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - 設計上 LLM 呼び出しはリトライ・バリデーションを行い、失敗時は安全にスキップ

- 市場レジーム判定
  - ETF 1321（Nikkei ETF）の 200日MA乖離とマクロニュースセンチメントを合成して日次で判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化

- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
  - トレーサビリティを UUID 連鎖で確保

- マーケットカレンダー管理
  - JPX カレンダーの差分取得・保存（calendar_update_job）
  - 営業日判定・前後営業日の取得等のユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）

---

## 必要条件（主な依存）

（プロジェクトルートの pyproject.toml / requirements.txt 等に依存関係をまとめる想定です。ここは実際のパッケージに合わせて調整してください）

- Python 3.10+
- duckdb
- openai
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

インストール例（pip）:
```
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

必須（利用する機能に応じて設定）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL / jquants_client）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知用チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等）

任意:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — デフォルト DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス。デフォルト: data/monitoring.db

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env および .env.local を自動読み込みします。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成し依存ライブラリをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   # または個別インストール
   pip install duckdb openai defusedxml
   ```
3. .env を作成（リポジトリに .env.example があれば参照）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```
4. DuckDB 用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
5. （オプション）KabuSys パッケージをインストール（開発インストール）
   ```
   pip install -e .
   ```

---

## 使い方（主要な例）

以下はライブラリ API の一部を利用するサンプルです。詳細は各モジュールを参照してください。

- DuckDB 接続と日次 ETL の実行:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は .env で上書き可能）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント集計（score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- マーケットカレンダー関連ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出し部は外部 API を利用するため `OPENAI_API_KEY` の設定が必要です。
- ETL / API 呼び出しはネットワークと API レートに依存します。ログや戻り値を確認して運用してください。
- ほとんどの処理はルックアヘッドバイアスを防ぐ設計になっています（target_date 未満・以前のみ参照する等）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要モジュールと役割です（リポジトリ内 `src/kabusys` を想定）。

- kabusys/
  - __init__.py — パッケージメタ（version, __all__）
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）および ETLResult
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py — RSS 取得・前処理・保存支援
    - quality.py — データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ用テーブル定義と初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（calc_momentum, calc_value, calc_volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

---

## 運用上の注意 / 実装上の留意点

- LLM（OpenAI）との統合部はリトライ・バリデーションを実装してありますが、API の利用料・レートには注意してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を尊重するため内部でレートリミタを備えています。同一時間帯で大量のリクエストを行う設計は避けてください。
- DuckDB に対する executemany といった操作はバージョン差（0.10 等）で挙動が異なる箇所を考慮しています（空リストの executemany を避ける等）。
- .env の自動読み込みは便利ですが、テスト環境などで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 追加情報 / 今後の拡張案

- 発注実装（kabuステーション連携）とリスク管理モジュールの追加
- バックテスト実行環境（ファクターの過去性能検証）
- モデル学習パイプライン（特徴量エンジニアリング → 学習 → 評価）
- 実稼働時の監視（Prometheus / ログ集約）やアラート

---

README は以上です。コードの詳細や使い方に関する具体的なサンプルや追加説明が必要であれば、どの機能について深掘りしたいか教えてください。