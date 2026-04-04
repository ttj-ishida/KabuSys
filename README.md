# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

KabuSys は日本株のデータ取得・ETL、ニュース NLP、因子計算、監査ログ設計、監視までを含むバックオフィス／リサーチ基盤のための Python ライブラリ群です。本リポジトリはライブラリ実装のみを含み、実行用 CLI やデプロイ設定は別途用意することを想定しています。

主な用途例:
- J-Quants API からの株価・財務・カレンダー取得（ETL）
- RSS ニュース収集と OpenAI による銘柄別センチメント算出（news_nlp）
- 市場レジーム判定（regime_detector）
- ファクター計算・特徴量解析（research）
- データ品質チェック（quality）
- 監査ログスキーマの初期化（audit）
- DuckDB を中心とした永続化

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の設計方針に従って構築されています。

- Look‑ahead bias を避ける（内部で date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB をデータ格納の主要 DB として利用（軽量で分析向け）
- J-Quants API / OpenAI API の呼び出しに堅牢なリトライ・レート制御を実装
- ETL は差分更新・バックフィルをサポートし、品質チェックで問題を検出
- 監査ログ（signal → order_request → executions のトレース）を厳密に保存

---

## 機能一覧

- Data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（fetch / save 各種）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 対策、URL 正規化）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- AI / NLP
  - ニュースセンチメント算出（score_news: 銘柄ごとの ai_score を ai_scores テーブルへ）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースを合成）

- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Z スコア正規化ユーティリティ

- 共通ユーティリティ
  - 環境設定読み込み（.env 自動読み込み、Settings）
  - 統計ユーティリティ、ETL 結果データクラス、ロギングへの配慮

---

## セットアップ手順

以下は開発環境でライブラリを使うための最低手順例です。

1. Python (推奨: 3.10+) 仮想環境作成
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使う想定。なければ主要依存を手動で入れてください。
   ```bash
   pip install duckdb openai defusedxml
   ```
   （その他、テストや運用で必要なパッケージがあれば追加してください）

3. プロジェクトをインストール（開発モード）
   プロジェクトに setup/pyproject がある場合:
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env の用意
   - ルートに `.env`（および開発用に `.env.local`）を置くと自動でロードされます（※パッケージ内の config モジュールがプロジェクトルートを検出して読み込みます）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（例）は次節にまとめます。

5. データディレクトリの作成（必要に応じて）
   デフォルトの DuckDB 保存先は `data/kabusys.duckdb`（settings.duckdb_path）です。必要に応じて親ディレクトリを作成してください。

---

## 環境変数（主要）

- 必須（ETL / J-Quants を使う場合）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使われる）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注機能を使う場合）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで参照）
  - 代替として score_* 関数の api_key 引数に渡すことも可能

- 任意（通知等）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

- 設定に関するその他（デフォルト値あり）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など（監視関連）

注意: config.Settings は .env（または OS 環境）から値を読み、必須キーが未設定だと ValueError を投げます。

---

## 使い方（簡易サンプル）

以下はライブラリをインポートして主要機能を呼ぶ例です。全て Python スクリプト内で実行できます。

- DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの算出（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境で設定されているか、api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB／スキーマ初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル作成後の接続を返します
```

- 市場カレンダー更新バッチ（calendar_update_job）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

注意点:
- OpenAI とのやり取りは API レートやコストに注意してください。score_* 関数はバッチ・再試行・フォールバック（失敗時は 0.0 等）を組み込んでいますが、実行ごとのコストは発生します。
- ETL 関数は内部で J-Quants への API 呼び出しと DuckDB への保存を行います。J-Quants の利用には有効なリフレッシュトークンが必要です。

---

## 実行例: スクリプトからの日次処理

簡易的な runner.py の例:
```python
# runner.py
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

def main():
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

if __name__ == "__main__":
    main()
```

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数処理と Settings クラス（.env 自動ロード、必須キーチェック）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースをまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込む
    - regime_detector.py  — ETF（1321）MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー判定とバッチ更新ジョブ
    - etl.py                 — ETL 結果クラス再エクスポート
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               — 監査ログ（signal/order/execution）スキーマと初期化
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py      — RSS 収集、記事正規化、SSRF 対策
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py— 将来リターン、IC、統計サマリー、rank
  - monitoring / strategy / execution / ... （パッケージ公開用に __all__ 指定あり）

（上記は本リポジトリで提供される主なモジュールの一覧です。詳細は各モジュールの docstring を参照してください。）

---

## 注意事項 / 運用上のヒント

- セキュリティ:
  - RSS 取得時は SSRF 対策を組み込んでいますが、実運用では受信元の管理・監査を徹底してください。
  - .env / シークレットは適切に保護してください（リポジトリにコミットしないこと）。
- テスト:
  - OpenAI や外部 API 呼び出しはモック化してユニットテストを行ってください（モジュール内に差し替えしやすいヘルパーが用意されています）。
- 運用:
  - ETL のスケジューリングは cron や Airflow 等で管理してください。run_daily_etl は単一日次実行に適します。
  - audit スキーマは初期化後は削除しない前提でデザインされています（監査ログの保持）。

---

ご不明点や README に含めたい追加の操作例（例: 発注フローの使い方、監視 / デーモン化手順など）があれば教えてください。必要に応じて実行コマンド例や environment サンプルのテンプレート（.env.example）も作成します。