# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データETL、ニュースNLP（LLM によるセンチメント）、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを備え、バックテスト／本番運用のための共通機能群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数一覧
- 注意点・設計方針
- ディレクトリ構成（モジュール説明）

---

## プロジェクト概要
KabuSys は日本株を対象としたデータ基盤と自動売買に必要なユーティリティ群をまとめた Python パッケージです。  
主に以下を目的とします。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- ニュース収集・NLP による銘柄ごとのセンチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算・特徴量探索（リサーチ用）
- 発注・約定に関する監査ログテーブル（冪等・トレース可能）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の重要点として「ルックアヘッドバイアス防止」「冪等性」「API リトライ / レート制御」「安全な RSS / HTTP 処理」などが組み込まれています。

---

## 機能一覧
主な機能（抜粋）：

- data.jquants_client
  - J-Quants API からの取得（daily quotes / financials / market calendar / listed info）
  - レートリミット・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT を利用）
- data.pipeline / etl
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 収集（URL 正規化、SSRF 対策、XML 安全パース）
  - raw_news テーブルへの冪等保存ロジック
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェックと QualityIssue レポート
- data.audit
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - init_audit_db / init_audit_schema（UTC タイムゾーン固定）
- ai.news_nlp
  - OpenAI を使ったニュースセンチメントのバッチ評価（JSON モード、チャンク）
  - API エラー時のリトライ・バリデーション・スコアクリッピング
- ai.regime_detector
  - ETF (1321) の MA200 乖離＋マクロニュースセンチメントの組合せで市場レジーム判定
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、z-score 正規化
- config
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 環境設定のラッパー（settings）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   (pyproject.toml / setup がある前提で)

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な Python パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （その他 requests 等、環境に応じて依存を追加）

   pyproject / requirements がある場合はそちらを利用してください。

3. 環境変数設定
   プロジェクトルートに `.env` と `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。  
   テスト時に自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要環境変数は次節参照。

4. DuckDB（データベース）準備
   デフォルトの DuckDB パスは `data/kabusys.duckdb`（設定で変更可）です。初回は監査テーブル等を初期化します:

   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # もしくは ":memory:"
   ```

---

## 簡単な使い方（コード例）

- settings と DB 接続

```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（例: 今日の ETL）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（ai.news_nlp.score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API Key は環境変数 OPENAI_API_KEY か api_key に指定
print(f"scored {n_written} symbols")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（別ファイルで分けたい場合）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # transactional=True による初期化も可能
```

- J-Quants から生データを直接取得（テスト用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
```

---

## 環境変数一覧（主要）
以下は config.Settings で参照される主な環境変数（必須は明記）。

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン（get_id_token で ID トークンを取得）
- KABU_API_PASSWORD (必須)  
  - kabu ステーション API 用のパスワード
- KABU_API_BASE_URL (任意)  
  - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH  
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH  
  - デフォルト: data/monitoring.db
- PID_FILE_PATH  
  - デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT  
  - 監視閾値（デフォルト 90, 85, 90 等）
- KABUSYS_ENV  
  - 値: development / paper_trading / live（デフォルト development）
- LOG_LEVEL  
  - 値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY  
  - OpenAI 呼び出しに使う API キー（ai モジュールは api_key 引数でも受け取れます）
- KABUSYS_DISABLE_AUTO_ENV_LOAD  
  - 1 を設定すると .env 自動読み込みを無効化

---

## 注意点・設計方針（抜粋）
- Look-ahead bias 対策  
  - ai / research の関数は内部で datetime.today() を直接参照しない設計。target_date を明示的に渡すことを想定しています。
- 冪等性  
  - 保存関数は ON CONFLICT を使い冪等にデータを更新します（ETL の再実行に安全）。
- API 安全対策  
  - J-Quants クライアントはレート制御、指数バックオフ、401 リフレッシュ対応を実装しています。
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml を利用した安全な XML パースを行います。
- フェイルセーフ  
  - LLM 呼び出しや外部 API の失敗は、致命的に停止させずフォールバック動作（例: スコア 0.0）で継続する所が多いです（ログを出力）。
- テスト容易性  
  - OpenAI コールや URL オープンなどは関数をモックできるように設計されています（単体テストに適する）。

---

## ディレクトリ構成（主要ファイルの説明）
（src/kabusys 以下）

- __init__.py  
  - パッケージの公開 API（version = 0.1.0）

- config.py  
  - .env 自動読込、Settings クラス（環境変数ラッパー）

- ai/
  - __init__.py
  - news_nlp.py  
    - ニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores テーブルへ書込
  - regime_detector.py  
    - ETF(1321)のMA200乖離とマクロニュースのLLMセンチメントを組合せ市場レジームを判定

- data/
  - __init__.py
  - jquants_client.py  
    - J-Quants API クライアント（取得・保存ユーティリティ・認証）
  - pipeline.py  
    - ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py  
    - ETLResult の再エクスポート
  - news_collector.py  
    - RSS 収集と前処理、raw_news への保存
  - quality.py  
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py  
    - zscore_normalize 等、研究で使う統計ユーティリティ
  - calendar_management.py  
    - JPX 市場カレンダーの管理・営業日判定・calendar_update_job
  - audit.py  
    - 監査ログ（signal_events / order_requests / executions）の DDL、初期化関数
  - (その他: monitoring 関連、pipeline の補助等)

- research/
  - __init__.py
  - factor_research.py  
    - Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py  
    - 将来リターン計算、IC、統計サマリ、rank 関数

---

## 追加情報・ヒント
- OpenAI 呼び出しはコストがかかるため、テスト時は API 呼び出し関数をモックしてください。モジュール内の _call_openai_api は unittest.mock で差し替え可能です。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、実装でチェックしています（ETL 保存処理参照）。
- news_collector の RSS 正規化処理では utm_* 等のトラッキングパラメータを除去して記事の冪等性を確保します。
- 監査ログ（audit）は削除を想定していません。トレース保持を重視した設計です。

---

README はここまでです。実行時の具体的な操作やスクリプト化（systemd / cron / Airflow などでのスケジューリング）は利用環境に合わせて実装してください。必要であれば「運用手順」や「デプロイ例（systemd / Docker / Compose）」のテンプレートも作成します。どの情報を追加しましょうか？