# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（オーダー → 約定のトレース）、マーケットカレンダー管理、データ品質チェックなどを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API 経由で株価日足、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（ページネーション対応・レート制御・自動トークンリフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）をサポート
  - 日次 ETL パイプライン（run_daily_etl）を提供

- ニュース収集・NLP
  - RSS フィードからニュースを収集して raw_news に格納
  - defusedxml を用いた安全な XML パース、SSRF 対策、受信サイズ制限などの堅牢な実装
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出（score_news）

- マクロ / 市場レジーム判定
  - ETF（1321）の200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を判定（score_regime）

- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）やファクター統計サマリー等の解析ユーティリティ

- データ管理 / 品質
  - マーケットカレンダー管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）および問題の収集（QualityIssue）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - UUID によるトレーサビリティ、冪等キー管理、UTC タイムスタンプ運用

- 設定管理
  - 環境変数（.env, .env.local）の自動読み込み（必要に応じて無効化可）
  - settings オブジェクト経由で各種設定を取得

---

## 必要条件 / 依存パッケージ

最低限必要な Python のバージョンは 3.10+ を想定しています（型アノテーションの記法や __future__ の利用に依存）。

主な Python 依存パッケージ（例）:
- duckdb
- openai
- defusedxml

（プロジェクト側で requirements.txt / pyproject.toml が用意されている場合はそちらを参照してください）

---

## 環境変数（主要なもの）

このプロジェクトは環境変数から各種キーやパスを取得します。少なくとも以下を設定してください（.env に記載してプロジェクトルートに置くと自動ロードされます）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に参照）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB 等）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env ロードを無効にする（テスト等で有用）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （開発時は flake8, pytest 等を追加）

   あるいはプロジェクトに pyproject.toml / requirements.txt があれば:
   - pip install -e .
   - または pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を作成
   - .env.example がある場合は参考にしてください

5. DuckDB 初期化（監査 DB 等）
   - Python スクリプトから init_audit_db を呼び出して監査 DB を初期化できます（下記を参照）。

---

## 使い方（主要な例）

以下は簡単な利用例です。DuckDB を使う前提での呼び出し例を示します。

- 日次 ETL の実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 対象日（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込み件数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

- 監査ログ（テーブル）を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: でも可
# conn をアプリケーションで使い続けられます
```

- 設定の取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## API の設計上の注意点 / 運用上の注意

- Look-ahead bias（先読みバイアス）対策が各所で組み込まれています:
  - 日次判定関数は内部で datetime.today() を直接参照しない設計
  - DB クエリは target_date 未満、または明示的なウィンドウを使いルックアヘッドを防止

- 外部 API の呼び出しにはリトライ / バックオフとフェイルセーフが実装されていますが、API レートやコストには注意してください。
  - J-Quants: rate limit（120 req/min）に合わせた RateLimiter を使用
  - OpenAI 呼び出しはリトライ等を行いますが、失敗時は安全側のデフォルト（スコア0）に戻す挙動

- セキュリティ / 安全対策
  - news_collector では SSRF 対策（ホスト検査 / リダイレクト検査）や XML の安全パース（defusedxml）を実装
  - .env の取り扱いや API キーの管理は十分に注意してください

- DuckDB の executemany は DuckDB バージョンにより空リストの取り扱いに差異があるためコード内でガードしています

---

## ディレクトリ構成（抜粋）

プロジェクトは src レイアウトで提供されています。主要モジュールを抜粋して示します：

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の公開
    - news_collector.py  — RSS 収集
    - calendar_management.py — マーケットカレンダー管理
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計解析
  - ai/ (上記)
  - research/ (上記)
  - その他: strategy / execution / monitoring などのパッケージ名が __all__ に含まれています（実装は今後拡張想定）

---

## テスト / 開発メモ

- 自動 .env ロードは config モジュール起動時に実行されます。テスト時に自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しは内部で _call_openai_api を経由しており、テスト時は unittest.mock.patch による差し替えが想定されています（モック化しやすい設計）。
- DuckDB を使ったユニットテストは ":memory:" 接続で行えます（init_audit_db は ":memory:" を受け付けます）。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンス情報や貢献ガイドラインを記載してください。リポジトリに LICENSE や CONTRIBUTING.md を追加することを推奨します。）

---

この README はコードベースの主要機能と基本的な利用方法をまとめたものです。より詳細なドキュメント（API リファレンス、運用手順、デプロイ手順、テストケース等）は別途作成することを推奨します。必要であれば README の翻訳（英語版）や各モジュールの簡易ドキュメント化を支援します。