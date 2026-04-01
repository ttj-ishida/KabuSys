# KabuSys

バージョン: 0.1.0

KabuSys は日本株用のデータプラットフォーム・リサーチ・自動売買支援ライブラリです。J-Quants など外部データソースからデータを取得・整備（ETL）し、特徴量（ファクター）計算、ニュース NLP によるセンチメント評価、マーケットレジーム判定、監査ログ用スキーマなど、自動売買システム構築に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today() を不用意に使わない等）
- DuckDB を用いたローカルデータベース中心の設計
- 冪等性（ETL / 保存処理は上書きロジックを採用）
- 外部 API 呼び出しにはリトライ / バックオフ / フェイルセーフを実装

---

## 機能一覧（主要機能）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出、無効化フラグあり）
  - 必須環境変数取得 API（settings オブジェクト）
- Data（データプラットフォーム）
  - J-Quants クライアント（株価/財務/カレンダーの取得、認証・リトライ・レート制限）
  - ETL パイプライン（run_daily_etl 等）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS を取得して raw_news に保存、SSRF対策・トラッキング除去等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ（signal_events / order_requests / executions 等）と初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore 正規化等）
- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク化）
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント算出（score_news）
  - マクロニュース + ETF MA乖離での市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンス検証を重視
- その他
  - 設定・ログレベル・実行環境（development/paper_trading/live）の管理

---

## 必要条件

- Python 3.10 以上（typing における PEP 604 の `|` を利用）
- 依存パッケージ（最低限）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （リポジトリ URL を指定）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに packaging / extras がある場合は `pip install -e .` など適宜実行してください）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の存在する階層）に `.env` または `.env.local` を置くと自動で読み込まれます（プロジェクト配布後でも動作するように __file__ を基点にルートを特定します）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定する

5. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
   - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 等）
   - （オプション）DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / LOG_LEVEL / KABUSYS_ENV

   settings オブジェクト（kabusys.config.settings）から各値を取り出せます。未設定の必須値は ValueError を送出します。

---

## 使い方（代表的な例）

以下はライブラリの主要な API を呼ぶ最小例です。実行前に環境変数を適切に設定してください。

- DuckDB 接続の作成例（デフォルトのパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定して ETL を実行（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア取得
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログテーブル初期化（専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後、audit_conn を用いて監査ログを書き込む
```

- ファクター計算（Research）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意:
- OpenAI API 呼び出し部にはリトライやフェイルセーフが実装されています。テスト時は内部の _call_openai_api をモックできます（kabusys.ai.news_nlp._call_openai_api 等）。
- ETL / データ操作は DuckDB 接続を直接受け取ります。トランザクション管理や接続ライフサイクルは呼び出し側で行ってください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime 等で使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス管理用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動的に .env / .env.local を読み込む実装です（プロジェクトルート検出）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（概要）

プロジェクトは src/kabusys 以下にパッケージ化されています。主要ファイルと説明：

- src/kabusys/__init__.py
  - パッケージエントリ（__version__=0.1.0）

- src/kabusys/config.py
  - 環境変数管理（.env ロード、自動検出、settings オブジェクト）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄別に集約して OpenAI で評価し ai_scores に書き込む
  - regime_detector.py — ETF 1321 の MA200 とマクロニュースで市場レジームを判定

- src/kabusys/data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
  - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py — 日次 ETL パイプライン実装（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ用 DDL / 初期化ユーティリティ
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - news_collector.py — RSS 取得と raw_news 保存（SSRF 対策等）

- src/kabusys/research/
  - __init__.py — 研究用ユーティリティの再エクスポート
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリーなど

（各モジュールは README 本文で触れたとおりの責務を持ちます）

---

## 運用上の注意

- ETL / 研究モジュールは基本的に DuckDB 接続を受け取り SQL と Python で処理します。実行環境での DB 管理（バックアップやファイル配置）に注意してください。
- OpenAI や J-Quants 呼び出しには API 制限があります。実運用では API キーの管理・レート制御・コスト管理を行ってください。
- ニュース収集は外部 RSS に依存します。RSS の取得で SSRF 対策や最大応答サイズチェックを実装していますが、運用時は取得対象ソースを限定することを推奨します。
- 監査ログ（audit スキーマ）は削除しない前提の設計です。必要に応じて retention policy を実装してください。

---

## テスト / 開発時のヒント

- OpenAI 呼び出しは内部で再利用関数をモックすることでテストしやすく設計されています（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- 自動 .env ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと CI やユニットテストで外部設定の影響を抑えられます。
- DuckDB を ":memory:" で初期化するとテスト用のインメモリ DB が利用できます（audit.init_audit_db もサポート）。

---

## ライセンス / 貢献

（この README はコードベースの説明に特化しています。ライセンスやコントリビューションガイドはプロジェクトルートの別ファイルに置いてください。）

---

問題や補足してほしい点があれば教えてください。使い方の具体的なユースケース（ETL のスケジュール設定、news_collector の実行フロー、監査ログ連携など）に合わせた例も追加作成します。