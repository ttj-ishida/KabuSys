# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログなどを含むモジュール群を提供します。

主な想定用途：
- J‑Quants API を使った株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を使った銘柄センチメント集約
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（研究用途）
- 発注監査ログ（監査テーブルの初期化／管理）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env について）
- 使い方（簡易サンプル）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と研究／実行レイヤーをまとめた Python モジュール群です。  
主に DuckDB をデータストアに用い、J‑Quants API からデータを取得して ETL を実行、ニュースの NLP に OpenAI（gpt-4o-mini 想定）を使用する設計になっています。自動ロードされる .env を通じて各種 API キーなどの設定を管理します。

---

## 機能一覧

- データ取得・ETL
  - J‑Quants API クライアント（差分取得／ページネーション）
  - ETL パイプライン（株価・財務・カレンダー）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理 / NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ削除）
  - OpenAI を用いた銘柄センチメント集約（ai_scores への書き込み）
  - マクロニュースと ETF MA 乖離を組合せた市場レジーム判定
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター算出
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを含む監査スキーマ定義と初期化
- 設定管理
  - 自動 .env 読み込み（.env, .env.local の優先度処理、環境変数の保護）

---

## セットアップ手順

前提：Python 3.10+（コード中で型注釈に union | を使用しているため）を想定。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそちらを使用してください。）

   注意：
   - DuckDB のバージョンはコードコメントで互換性に触れています（例: DuckDB 0.10 の executemany 空リスト制約など）。
   - OpenAI Python SDK（v1 系、OpenAI(api_key) を用いる実装）を想定しています。

3. データディレクトリ作成（デフォルトパスを使う場合）
   ```
   mkdir -p data
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（詳細は下節参照）。

---

## 環境変数（.env の挙動）

config モジュールは以下の優先順位で自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）：

- OS 環境変数（最優先）
- .env.local（存在すれば上書き）
- .env（上書きはしない）

主に使う環境変数（必須/任意）：
- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for NLP functions unless you pass api_key 引数)
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注等で使用）
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須 if Slack notification code used)
- SLACK_CHANNEL_ID (必須 if Slack notification code used)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視関連）
- KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env のパースは一般的な shell 形式（export KEY=val / KEY="val" / コメント）に対応しています。引用符やエスケープも考慮されます。

---

## 使い方（簡易サンプル）

以下は基本的な使用例です。実運用ではロギング設定や例外処理、API キー管理を適切に行ってください。

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数に設定するか api_key を渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
```

- 監査 DB 初期化（独立した監査用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査ログを書き込めます
```

- 設定の参照（settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

注意点：
- OpenAI 呼び出しはリトライ・エラー時のフォールバックを実装していますが、API キーが必須です（score_news / score_regime は未設定時に ValueError を投げます）。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を目標に実装されています。
- DuckDB の executemany に対する注意（空リストバインド）やバージョン依存の挙動についてはコード内コメントを参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と概要です。

- kabusys/
  - __init__.py
  - config.py
    - 環境設定の自動読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI でのセンチメント算出（score_news）
    - regime_detector.py
      - ETF(1321) MA200 乖離 + マクロニュース LLM を合成して市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py
      - ETL のエントリポイント（run_daily_etl 等）と ETLResult
    - jquants_client.py
      - J‑Quants API クライアント（fetch / save 系）
    - news_collector.py
      - RSS 収集・前処理・raw_news 登録（SSRF 対策等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の共通統計ユーティリティ
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
    - audit.py
      - 監査ログの DDL/初期化（init_audit_schema / init_audit_db）
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - ファクター算出（モメンタム / ボラティリティ / バリュー）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、rank 等

（上記はコードベースの一部抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 開発 / テストのヒント

- 自動 .env ロードを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テストで環境を独立させたいときに便利です。

- OpenAI 呼び出しはテストでモックしやすいよう、内部の API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）を patch できます。

- DuckDB の初期スキーマが必要な場合は、プロジェクト内にスキーマ初期化用のユーティリティ（data.schema 相当）を呼び出してテーブルを作成してください（audit.init_audit_db や各保存関数はテーブル前提です）。

---

必要であれば README に含めるサンプルの追加（例: systemd サービス定義、cron での ETL 実行例、Slack 通知の使い方）や、より詳細な API リファレンス（各関数の引数説明・戻り値・例外）を追加できます。どの情報を優先して拡張しますか？