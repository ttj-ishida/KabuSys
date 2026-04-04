# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM ベースのニュース分析、ファクター計算・研究ユーティリティ、監査ログ用スキーマなどを含むモジュール群を提供します。

---

## 概要

KabuSys は次の用途を想定した Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー等データの差分 ETL
- RSS ニュース収集と前処理（raw_news テーブルへの保存）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算・探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal / order_request / execution）用の DuckDB スキーマと初期化ユーティリティ
- 環境変数管理（プロジェクトルートの .env / .env.local 自動読込）

設計方針としては、Look‑ahead バイアス回避、冪等性（DB 保存は ON CONFLICT）、堅牢な API リトライ/バックオフ、外部依存を最小化した実装（標準ライブラリ＋必要最小限の外部パッケージ）を目指しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl：市場カレンダー、株価、財務の差分取得・保存・品質チェック
  - ページネーション対応・トークン自動リフレッシュ・レート制御（J-Quants）

- データ管理
  - DuckDB を前提とした保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
  - audit モジュールで監査用テーブル（signal_events / order_requests / executions）を作成・初期化

- ニュース & AI
  - RSS 取得／記事前処理（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント score_news
  - ETF（1321）MA200 とマクロニュースの LLM センチメントを合成した市場レジーム判定 score_regime

- 研究（Research）
  - ファクター計算：calc_momentum / calc_value / calc_volatility
  - 特徴量探索：calc_forward_returns / calc_ic / factor_summary / rank
  - 汎用統計：zscore_normalize

- 品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue レポート）

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）と Settings API（settings）

---

## セットアップ手順

※このリポジトリがパッケージとして配布されている前提ではなく、ソースを直接利用する前提の手順です。

1. Python 環境を用意（推奨: Python 3.10+）
2. 必要パッケージをインストール

   最低限必要な外部ライブラリ（コード内参照）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置して設定できます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（注文実行等）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : デフォルトデータベースパス（data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（data/monitoring.db）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/…）
   - KABUSYS_ENV           : development / paper_trading / live

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は主要ユーティリティの使用例です。実行前に環境変数を正しく設定してください。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL の実行（日次）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定するか省略して今日を対象にする
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄別）を生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（既存 DuckDB にテーブルを追加）
```python
from kabusys.data.audit import init_audit_schema

# 既に作成済みの conn を渡す
init_audit_schema(conn, transactional=True)
```

- 監査専用 DB を新規作成して初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/monitoring_audit.duckdb"))
```

- ファクター計算・研究ユーティリティの使用例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意:
- score_news / score_regime は OpenAI API を呼び出します。環境変数 OPENAI_API_KEY をセットするか、api_key 引数で渡してください。
- J-Quants API 呼び出しを行う関数は JQUANTS_REFRESH_TOKEN を必要とします。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu ステーション API のベース URL（省略時ローカル）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_ENV — 環境（development | paper_trading | live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする（1 で無効）

---

## ディレクトリ構成（主なファイル）

プロジェクト内の主なモジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理（.env 自動読み込み / Settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS ニュース収集と前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - research/... (その他ユーティリティ)

各ファイルは README 上で説明したそれぞれの機能を実装しています。関数 docstring に詳細な設計方針や制約（Look‑ahead 回避、トランザクション挙動、リトライ方針など）が記載されていますので、実際に利用する際は該当ファイルの docstring を参照してください。

---

## 注意事項 / 運用上のヒント

- Look‑ahead バイアスに注意：
  - 研究・バックテスト用途で利用する際は、ETL により取り込んだ時刻（fetched_at）や `target_date` の取り扱いに注意してください。モジュールは Look‑ahead の影響を避ける設計を意識していますが、利用側でも過去のみのデータ参照を厳密に管理してください。
- OpenAI 呼び出しはコストとレイテンシを伴います。バッチサイズやトークン量、モデル（デフォルト gpt-4o-mini）設定は運用に合わせて調整してください。
- DuckDB の executemany に空リストを渡すと互換性問題が発生するバージョンがあるため、コード側で空チェックが行われています。直接 SQL を編集する場合に注意してください。
- .env の読み込みロジックはプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト環境等で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

問題点や追加したいドキュメントの詳細（例：API リファレンス、運用 Runbook、Docker 化手順など）があれば教えてください。必要に応じて README を拡張します。