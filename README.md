# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）→ 品質チェック → データ永続化（DuckDB）→ ニュースの NLP スコアリング → 市場レジーム判定 → リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）までを想定したモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「堅牢な外部 API 呼び出し（リトライ・バックオフ・レート制御）」「DB 側での一貫性確保（ON CONFLICT）」です。

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（Settings クラス）
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（差分取得、ページネーション対応）
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL の集約実行（run_daily_etl）と結果オブジェクト（ETLResult）
- データ品質チェック
  - 欠損（OHLC）チェック、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集・前処理
  - RSS フィード収集、URL 正規化（トラッキングパラメータ除去）、SSRF 対策、記事 ID 生成
- ニュース NLP（OpenAI）
  - 銘柄別ニュース統合 → LLM によるセンチメントスコア取得（JSON Mode）
  - チャンク処理・リトライ・レスポンス検証・スコアのクリップ
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日 MA 乖離 と マクロニュースの LLM センチメントを合成して日次レジーム判定
- リサーチ（ファクター）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）、統計サマリー
  - Z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 監査 DB の初期化（init_audit_db）
- J-Quants クライアント
  - レート制限管理、トークン自動リフレッシュ、リトライ、保存関数（DuckDB へ冪等保存）

## セットアップ手順

以下はローカルで開発・実行するための基本手順です。

1. Python 環境
   - Python 3.10 以上を推奨（typing 機能を多用しています）。
2. 依存パッケージをインストール
   - requirements.txt を用意している前提で：
     - pip install -r requirements.txt
   - 主な必須パッケージ（コード参照）:
     - duckdb
     - openai
     - defusedxml
3. プロジェクトルートの .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数を設定します:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必要）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト data/monitoring.db）
     - PID_FILE_PATH／しきい値設定（監視関連）
5. プロジェクトの初期化（監査 DB など）
   - 監査 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

例: .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

注意: トークン・パスワード等は漏えいしないように管理してください。

## 使い方（主要な API と例）

以下は主要ユースケースの最小例です。実行前に .env を準備し、依存パッケージをインストールしてください。

- DuckDB 接続準備（ETL や AI 関数で使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略可: 今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコアを ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が保存されます
```

- 監査ログ（監査 DB 初期化）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み／参照が可能
```

- リサーチ用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

## 設定の自動読み込み挙動（config.py のポイント）

- パッケージインポート時にプロジェクトルートを .git または pyproject.toml を基準に探し、以下の順で .env ファイルを読み込みます:
  - 既存の OS 環境変数を尊重（上書きしない）
  - .env（override=False）
  - .env.local（override=True、.env の値を上書き）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラス経由で必須環境変数の取得を行います（未設定時は ValueError）。

## ディレクトリ構成

（src/kabusys 以下の主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数/設定の自動ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM による銘柄別スコアリング（score_news）
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py — ETL の主エントリ（run_daily_etl 等）と ETLResult
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - jquants_client.py — J-Quants API クライアント（fetch_* / save_*）
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（QualityIssue 等）
    - audit.py — 監査テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

## 開発・テストに関するメモ

- OpenAI 呼び出しやネットワーク系関数は内部で _call_openai_api / _urlopen 等のラッパー関数を使っており、ユニットテスト時はこれらを patch して差し替えることで外部依存を排除できます。
- DuckDB を使うため、テスト時は ":memory:" を指定してインメモリ DB を使うことが可能です（init_audit_db でも ":memory:" をサポート）。
- .env の自動ロードはテスト時に副作用となることがあるため、KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、必要な環境変数を明示的にセットしてください。

## セキュリティ・運用上の注意

- API キー・トークン類（J-Quants、OpenAI、Slack、kabu API パスワード等）は厳重に管理してください。リポジトリにコミットしないでください。
- news_collector は SSRF 対策（リダイレクト検査、プライベート IP 検査）や応答サイズ制限を実装していますが、運用時にはダウンストリームの脆弱性も考慮してください。
- run_daily_etl 等の夜間バッチは、RateLimit（J-Quants）や API の利用制限を守るよう設計されています。実運用ではジョブスケジューラ（cron / Airflow 等）での稼働管理を推奨します。

---

詳細な API ドキュメントや実行スクリプト（CLI）を付けることで、さらに導入を容易にできます。必要であれば README を拡張して、具体的な .env.example、requirements.txt、サンプル cron エントリ、監視アラート（Slack）連携例なども追加します。どの追加情報が必要か教えてください。