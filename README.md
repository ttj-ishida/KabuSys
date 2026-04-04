# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ。  
J-Quants からのデータ ETL、ニュース収集・LLM によるセンチメント解析、市場レジーム判定、研究用ファクター計算、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムおよびデータプラットフォーム向けの内部ライブラリ群です。主に以下を目的としています。

- J-Quants API を用いた株価／財務／マーケットカレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）および統計ユーティリティ
- 監査（signal → order_request → executions）用の冪等テーブル定義／初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストでのルックアヘッドバイアスを避ける実装（日時の明示的引数使用、データの排他条件など）がされています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証自動リフレッシュ、レートリミット、ページネーション）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS 取得・前処理・保存）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化等）
- ai
  - ニュース NLP（銘柄別センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント → score_regime）
  - OpenAI 呼び出しはリトライや 5xx ハンドリングを備え、失敗時は中立値にフォールバックする設計
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, 統計サマリー 等）
- config
  - .env / .env.local / 環境変数の自動ロード（プロジェクトルート判定。無効化フラグあり）
  - アプリ設定ラッパ（Settings）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈 Path | None 等を使用）
- ネットワーク経由で API を呼べる環境

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo>
   cd <repo>
   pip install -e .
   ```

2. 必要な依存パッケージ（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動でロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須・またはよく使うもの）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で利用）
   - KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - その他監視・閾値設定（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT ...）

   ※ .env の優先順位: OS 環境変数 > .env.local > .env

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

下記は最小限の Python スニペット例です。実際はエラーハンドリングやログ設定を追加してください。

- DuckDB 接続準備（設定を利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジーム判定を実行して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(str(settings.duckdb_path))  # または別パスを指定
```

- 研究用ファクター計算例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

注意:
- score_news / score_regime は OpenAI API を使用します。API 呼び出しに失敗した場合、フェイルセーフとして中立値（0.0）等にフォールバックする設計です。
- ETL や news_collector は外部 API への接続を行うため、実行環境にネットワーク権限と API キーが必要です。

---

## .env の自動ロード（挙動）

- 自動ロードはデフォルトで有効。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- プロジェクトルートはこのモジュール自身の親ディレクトリから `.git` または `pyproject.toml` を探索して判定します（CWD に依存しない）。
- 読み込み順（優先度低 → 高）:
  - .env
  - .env.local（.env の値を上書き）
  - OS 環境変数（最優先）
- .env パースは shell ライクな `KEY=val`、`export KEY=val`、クォートやエスケープ、コメント等に対応します。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージの公開 API（data, strategy, execution, monitoring）
  - config.py — 環境設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS 収集 & 前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマの DDL と初期化
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — forward returns, IC, 統計サマリ等
  - ai/regime_detector.py, ai/news_nlp.py — OpenAI を用いる箇所はモデルや JSON Mode を利用し、エラーハンドリング・リトライを備える

（上記は主要なファイルの抜粋です。細かいユーティリティや定数は各モジュール内部にあります。）

---

## 実運用上の注意 / 補足

- 重要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は漏洩しないよう管理してください。
- OpenAI の出力は JSON モードで期待されますが、実際にはパースエラーが起きることがあるため、モジュールは失敗時に中立値で継続する設計です。
- J-Quants API はレート制限があるため、jquants_client では固定間隔スロットリングとリトライを実装しています。誤った高速ポーリングは避けてください。
- DuckDB の executemany 等、バージョン依存の制約に配慮した実装になっています（例: 空リストの executemany の扱い）。
- 監査テーブルは削除しない前提で設計されています。order_request_id は冪等キーとして二重発注防止に利用できます。

---

## 参考 / 連絡先

- このリポジトリには README のほかに設計ドキュメント（StrategyModel.md, DataPlatform.md 等）が参照されている箇所があります。実装と合わせて参照してください。
- バグ報告や設計変更提案は issue を立ててください。

---

README は以上です。必要であれば、具体的な .env.example のテンプレートや CI / デプロイ手順、ロギング設定例（logging.basicConfig 等）を追加で作成します。どの情報を優先して追加しますか？