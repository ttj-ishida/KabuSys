# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI 等の外部サービスと連携し、データ取得（ETL）、品質チェック、ニュース NLP によるセンチメント計算、ファクター計算、監査ログ管理、マーケットレジーム判定などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- DuckDB を使ったデータ保存と品質チェック
- RSS からのニュース収集・前処理と OpenAI を使った銘柄センチメント解析（ニュースNLP）
- ETF・ニュースを組み合わせた市場レジーム判定（LLM を利用）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注・約定までの監査ログスキーマ（監査テーブルの初期化・管理）

設計上の重点：
- ルックアヘッドバイアスを避ける（内部で datetime.now()/date.today() に依存しない設計箇所あり）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE 等で上書き）
- フェイルセーフ（外部 API 失敗時はゼロスコアなどで継続）
- テストしやすさ（API 呼び出しや時間依存を注入/モック可能）

---

## 主な機能一覧

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_* / save_* 系関数（ページネーション・リトライ・トークン再発行対応）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、raw_news への保存補助
- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄別にまとめ OpenAI でセンチメントスコアを算出し ai_scores へ保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
- リサーチ補助（kabusys.research）
  - ファクター計算（momentum / value / volatility）や IC / forward returns / 統計サマリ

---

## システム要件（推奨）

- Python 3.10 以上（型アノテーションに `X | Y` を使用しているため）
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- （任意）その他標準ライブラリ: urllib, logging, datetime など

推奨の requirements.txt（例）:
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン（パッケージが `src/` 配下に配置されている想定）
   - 例: git clone <repo-url>

2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e .

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須／主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須、ETL 用）
     - KABU_API_PASSWORD：kabuステーション API のパスワード（注文連携で使用）
     - OPENAI_API_KEY：OpenAI API キー（ニュースNLP / レジーム判定で使用）
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視等に使用: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他モニタ設定

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成
   - デフォルトの DB 保存先（例: data/）が存在しない場合は作成してください:
     - mkdir -p data

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプト内での利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の作成例:
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付け（score_news）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
print("scored:", n_written)
```

- 市場レジーム判定（score_regime）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（監査用独立 DB を作る例）
```
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- カレンダー更新バッチ（calendar_update_job）
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

補足:
- OpenAI 呼び出しは API 制限やエラー時のリトライを備えていますが、API キーやコスト管理に注意してください。
- ETL / API 呼び出しはネットワーク通信を伴うため、適切な権限・レート管理の元で実行してください。

---

## 自動 .env 読み込みの仕様

- パッケージ初期化時に自動で `.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml を基準）から読み込み、環境変数を設定します。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースはシェルスタイル（export KEY=val、引用符、コメント対応）で行います。

---

## ディレクトリ構成（主要ファイルの説明）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージのバージョンと公開サブパッケージ定義

- config.py
  - 環境変数の自動ロード・設定ラッパー（Settings クラス）
  - 必要な環境変数の取得ヘルパー（_require 等）

- ai/
  - __init__.py
  - news_nlp.py
    - ニュース記事を OpenAI に投げて銘柄ごとの ai_score を ai_scores テーブルに保存する処理
    - calc_news_window, score_news 等
  - regime_detector.py
    - ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新する score_regime

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API の取得・保存ラッパー（fetch/save_*, get_id_token）
    - レートリミッタ・リトライ・トークン自動リフレッシュ対応
  - pipeline.py
    - ETL の主要エントリ（run_daily_etl 等）及び ETLResult クラス
  - calendar_management.py
    - market_calendar の判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）と calendar_update_job
  - news_collector.py
    - RSS 取得・正規化・前処理・ID 生成・SSRF 対策など（fetch_rss, preprocess_text 等）
  - quality.py
    - データ品質チェック（missing, spike, duplicates, date consistency）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログテーブル定義（signal_events, order_requests, executions）と初期化補助（init_audit_schema / init_audit_db）
  - etl.py
    - ETLResult の再エクスポート（簡易インタフェース）

- research/
  - __init__.py
  - factor_research.py
    - calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials を参照）
  - feature_exploration.py
    - calc_forward_returns, calc_ic, factor_summary, rank（リサーチ用統計関数）

---

## 注意事項 / 運用上のポイント

- セキュリティ:
  - RSS の取得では SSRF 対策・プライベートアドレス拒否・Content-Length 上限などを実装していますが、運用環境ではネットワーク・プロキシ設定に注意してください。
  - OpenAI / J-Quants の API キーは漏洩しないように管理してください。
- Look-ahead バイアス:
  - 多くの関数は意図的に date 引数を受け取り、内部で現在時刻を直接参照しない設計になっています。バックテスト時にはこれを遵守してください。
- DuckDB:
  - 一部の executemany は空リストを受け付けない（DuckDB のバージョン差）ためチェックを行っています。DuckDB のバージョン互換性に注意してください。
- テスト:
  - OpenAI 呼び出しや外部 HTTP 呼び出しはモック可能な作りになっています（モジュール内の _call_openai_api などをパッチする等）。

---

## 追加リソース / 貢献

- バグ報告・機能要望は issue にお願いします。
- 外部 API の利用やコストに関するドキュメントは各サービス（OpenAI / J-Quants / kabuステーション）を参照してください。

---

README は開発の進行に合わせて更新してください。必要であればサンプルの .env.example や requirements.txt、簡易 CLI スクリプトなどを追加して運用を容易にすることを推奨します。