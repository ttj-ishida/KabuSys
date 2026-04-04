# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。ETL、データ品質チェック、ニュースセンチメント（LLM）、ファクター計算、監査ログ設計など、量的運用・研究から実運用までの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集と LLM を用いた銘柄センチメント算出（gpt-4o-mini を想定）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- DuckDB ベースのローカルデータレイクとの連携

設計方針は「ルックアヘッドバイアス防止」「冪等性」「堅牢なエラーハンドリング」「外部 API のリトライ・レート制御」です。

---

## 主な機能一覧

- data/jquants_client.py: J-Quants API クライアント（レートリミット・リトライ・IDトークン管理）
- data/pipeline.py: 日次 ETL パイプライン（run_daily_etl を公開）
- data/news_collector.py: RSS からのニュース収集（SSRF/サイズ制限/正規化）
- data/quality.py: データ品質チェック群（欠損・重複・スパイク・日付不整合）
- data/calendar_management.py: JPX カレンダー管理・営業日判定ユーティリティ
- data/audit.py: 監査ログスキーマの初期化・監査テーブル（冪等、UTC タイムスタンプ）
- data/stats.py: 汎用統計ユーティリティ（Zスコア正規化）
- research/*: ファクター計算（モメンタム/バリュー/ボラティリティ）と特徴量解析（IC, forward returns 等）
- ai/news_nlp.py: ニュースを銘柄ごとに LLM でスコア化し ai_scores に書き込むロジック
- ai/regime_detector.py: ETF(1321) の MA 乖離とマクロニュースを合わせて市場レジーム判定
- config.py: .env ファイルと環境変数管理（自動読み込み機能あり）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（型注釈やモダンな依存を利用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

1. リポジトリをクローンして開発モードでインストール
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
   ※ setup.py/pyproject.toml がある前提で editable install を使います。なければ必要な依存を pip で個別に入れてください。

2. 必要な Python パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の追加依存は pyproject.toml を参照）

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の準備
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。必要な主要キー:

   必須（機能に応じて）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY: OpenAI API キー（AI スコアリング・レジーム判定）

   任意・運用:
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文連携を行う場合）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化します（テスト用）

   .env の読み込みは、.git または pyproject.toml を探索してプロジェクトルートを特定してから行います。

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は主要なユースケースの最小例です。すべての呼び出しは DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を渡します。

- 設定オブジェクトを参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.jquants_refresh_token)
  ```

- DuckDB 接続を作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント算出（LLM を使う）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数に設定、または api_key 引数で指定可能
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("scored:", n_written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査データベース初期化（監査ログ用 DuckDB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  from pathlib import Path

  audit_conn = init_audit_db(Path("data/monitoring_audit.duckdb"))
  # audit_conn を使用して order/signals/executions を記録できるテーブルが作成される
  ```

- ファクター計算（研究用）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  factors = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- AI 関連機能は OpenAI API に依存します。API のレスポンス失敗時はフェイルセーフとして 0.0 や空スコアにフォールバックする設計です（例外を投げずに継続する箇所が多い）。
- J-Quants クライアントは内部でレートリミット制御とリトライを実装しています。id_token の自動リフレッシュも行います。

---

## ディレクトリ構成（主要ファイル説明）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、settings オブジェクト（各種設定取得）
- ai/
  - __init__.py
  - news_nlp.py : ニュース→銘柄ごとセンチメント（OpenAI 経由）→ ai_scores 書き込み
  - regime_detector.py : ETF MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（fetch / save / token）
  - pipeline.py : ETL パイプラインと run_daily_etl
  - news_collector.py : RSS 取得・前処理・raw_news 保存ロジック
  - calendar_management.py : market_calendar 管理 / 営業日判定ユーティリティ
  - quality.py : データ品質チェック（QualityIssue を返す）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログテーブル定義・初期化
  - etl.py : ETLResult の公開
- research/
  - __init__.py
  - factor_research.py : モメンタム/バリュー/ボラティリティ等の計算
  - feature_exploration.py : forward returns / IC / factor summary 等
- research/*, ai/*, data/* の各モジュールは DuckDB 接続を受け取り、バックテスト／研究用に副作用の少ない実装を心掛けています。

---

## 環境変数（要約）

主要な環境変数（.env に設定）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須: ETL 実行時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

config.Settings クラスから各値を参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token, settings.env, settings.duckdb_path)
```

---

## 運用・注意点

- ルックアヘッドバイアス対策: 多くのモジュール（news_nlp, regime_detector, research）は date 引数に基づく半開区間のデータ参照を行い、内部で datetime.now() を直接使わない設計です。過去データのみ参照することでバックテストの健全性を保ちます。
- 冪等性: J-Quants からの保存処理は ON CONFLICT DO UPDATE を使用しているため、再実行に強いです。
- OpenAI 呼び出し: レスポンスは JSON モードを期待しますが、パース失敗や API エラーはログに記録して 0.0 等にフォールバックします。レスポンス検証ロジックが組み込まれています。
- セキュリティ: news_collector では SSRF 対策、受信サイズ制限、defusedxml による XML パース保護を実装しています。
- DuckDB の互換性: 一部の実装は DuckDB バージョン特性を考慮しています（executemany の空リスト制約など）。

---

## 追加情報・拡張

- 監視・実行モジュール（execution / monitoring）はパッケージ export に含まれていますが、実際のブローカー連携や常駐プロセスの実装は別途実装される想定です。
- 研究用関数は外部ライブラリに依存しない純 Python 実装なので、必要に応じて NumPy/Pandas 版の高速化を検討できます。

---

README の補足やサンプルスクリプト（起動スクリプト、cron ジョブ例、Dockerfile 等）を追加したい場合は用途に合わせて追記可能です。必要な項目を教えてください。