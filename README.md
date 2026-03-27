# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（部分実装）。  
このリポジトリはデータ収集・ETL、ニュースNLP（LLMを用いたセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などのユーティリティ群を提供します。

> 注: 本READMEはソースツリー内の主要モジュール（kabusys/*.py）をもとに作成しています。戦略（strategy）、発注（execution）、監視（monitoring）などの実装は別途追加されることを想定しています。

## 主な特徴（機能一覧）

- 環境設定管理
  - .env ファイルおよび環境変数の自動読み込み（プロジェクトルート検出、読み込み優先順位あり）
  - 必須環境変数取得ヘルパ

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - ETL パイプライン（株価、財務、カレンダー差分取得と保存）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去・前処理）
  - マーケットカレンダー管理（営業日判定、next/prev/trading days）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal/order/execution トレーサビリティ）初期化ユーティリティ
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- AI / NLP（kabusys.ai）
  - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini 等）でセンチメントを算出し ai_scores に書き込む
  - マクロニュースとETF（1321）のMA乖離を組み合わせた市場レジーム判定（bull / neutral / bear）

- リサーチ（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク関数等

- 監査・トレーサビリティ
  - signal_events / order_requests / executions の DDL とインデックス、DB初期化関数（DuckDB）

## 必要条件（Prerequisites）

- Python 3.10 以上（ソースで `X | Y` の型注釈を使用）
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI などを利用する場合）
- J-Quants / OpenAI / Slack 等の API キー（環境変数）

## 環境変数（主要）

以下は本コード内で参照される代表的な環境変数です。プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。

必須（動作に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系が必要な場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う際に必要）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

.env を作る際は `.env.example` を参考にしてください（リポジトリに例がある想定）。

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 例（最小限）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成し、必要なキーを設定します（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）。
   - 自動読み込みを無効にしたいテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

5. データディレクトリの準備（必要に応じて）
   ```
   mkdir -p data
   ```

## 使い方（簡単な例）

以下は主要機能を Python REPL やスクリプトから呼ぶ例です。DuckDB 接続はファイルパスまたは ":memory:" を指定して取得します。

- DuckDB 接続の作成
  ```py
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（日次）を実行する
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（ai_news）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # 環境変数 OPENAI_API_KEY を設定しておくか api_key を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルへレコードが書き込まれます
  ```

- 監査ログ用 DB 初期化
  ```py
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- マーケットカレンダーの判定ユーティリティ
  ```py
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- リサーチファクターの計算
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意:
- AI 関連は OpenAI API を利用します。API キー未設定時は ValueError が発生します。
- ETL / J-Quants クライアントはネットワークアクセスと有効な J-Quants トークンを必要とします。
- DuckDB のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）は事前に作成しておくか、ETL/DDL 初期化ロジックを実行してください（モジュールには保存・DDL を行う関数が含まれます）。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄別に集約して OpenAI に送信、ai_scores へ保存
  - regime_detector.py — ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を算出
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理・営業日判定・calendar_update_job
  - etl.py — ETL インターフェース re-export
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック群（欠損、スパイク、重複、日付不整合）
  - audit.py — 監査ログ DDL / 初期化（signal_events / order_requests / executions）
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py — RSS 収集、前処理、raw_news への保存（SSRF対策等）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility ファクター
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
- （その他）strategy, execution, monitoring モジュールはパッケージ公開名に含まれますが、本スナップショットには詳細実装が含まれていない可能性があります。

## 運用上の注意・設計方針の要点

- Look-ahead バイアス防止:
  - 多くの処理で datetime.today() / date.today() の直接参照を避け、呼び出し側が target_date を指定する設計。
  - データの取得・分析は target_date を明示的に指定して使うことを推奨。

- フェイルセーフ:
  - AI API や外部 API の失敗は多くの箇所で安全にフォールバック（例: macro_sentiment=0.0）し、全体処理を停止させない方針。

- 冪等性:
  - J-Quants 保存関数や監査ログ初期化等は冪等に設計（ON CONFLICT / INSERT ... DO UPDATE など）。

- セキュリティ・堅牢化:
  - RSS 収集で SSRF/ローカルホストアクセス対策、XML パースに defusedxml を使用、レスポンスサイズ制限などを実装。

## テスト・開発ヒント

- 自動 .env 読み込みを回避したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- AI モジュールやネットワーク呼び出しは unittest.mock で _call_openai_api や _urlopen を差し替えてテストしやすく設計されています。

## サポート / 貢献

- バグ報告や機能要望は Issue を立ててください。  
- コントリビュートする場合は、ユニットテストと簡潔な説明を添えて PR をお願いします。

---

以上。導入・運用にあたって不明点があれば、どの機能についての使い方や実行例をさらに詳しく書くか教えてください。必要に応じてサンプルスクリプトや、想定される DB スキーマ（DDL）の抜粋も追加できます。