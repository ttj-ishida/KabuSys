# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、データ品質チェック、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「外部 API の堅牢なリトライとレート制御」「テスト容易性（API 呼び出し差し替え可能）」です。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API からの日足株価（OHLCV）取得（ページネーション・レート制御・トークン自動リフレッシュ）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得・保守
  - 差分取得・バックフィル・品質チェックを含む日次 ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
- データ品質チェック
  - 欠損データ、主キー重複、株価スパイク、日付不整合の検出（kabusys.data.quality）
- ニュース収集 / 前処理
  - RSS からのニュース取得（SSRF 対策、gzip/サイズ制限、URL 正規化、トラッキング除去）
  - raw_news / news_symbols への冪等保存ロジック（kabusys.data.news_collector）
- LLM を用いた NLP（OpenAI）
  - ニュースごとの銘柄センチメント算出（kabusys.ai.news_nlp.score_news）
  - マクロセンチメントと ETF (1321) の MA200 乖離を合成した市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - API 呼び出しはリトライ（429/ネットワーク/5xx）・JSON バリデーション・スコアクリッピング対応
- リサーチ / ファクター計算
  - Momentum、Value、Volatility、Liquidity 等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Spearman）・統計サマリー等
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化ユーティリティ（kabusys.data.audit）
  - init_audit_db で専用 DuckDB を初期化可能
- 設定管理
  - .env / .env.local / OS 環境変数の自動ロード（kabusys.config）
  - 必須環境変数チェックとプロパティ経由の取得

---

## 必要要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

※プロジェクトに requirements.txt/pyproject.toml がある想定で、適宜インストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（省略可能）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. パッケージと依存のインストール
   - 開発中に編集して使う場合:
     ```
     pip install -e .
     ```
   - あるいは requirements.txt / pyproject.toml に従ってインストール:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時等に便利）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API を使う場合の API キー

   任意/デフォルト
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite path（デフォルト: data/monitoring.db）

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトからの基本的な利用例です。

- ETL（日次パイプライン）の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーは環境変数か引数で）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
  print("scored:", n_written)
  ```

- 市場レジーム（マクロ + MA200）判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（別 DB に分けたいとき）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算 / リサーチユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- score_news / score_regime は OpenAI API を実際に呼び出します。テスト時はモック（unittest.mock.patch）して差し替えが可能です（モジュール内で呼び出し関数を分離しているため容易です）。
- run_daily_etl 等は DuckDB 接続を受け取ります。settings.duckdb_path を利用して接続するか、任意の接続を渡してください。

---

## 設定と自動ロードの挙動（kabusys.config）

- 自動ロード順: OS 環境変数 > .env.local > .env
- 自動ロードを無効にする環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須取得プロパティ:
  - settings.jquants_refresh_token  (JQUANTS_REFRESH_TOKEN)
  - settings.kabu_api_password     (KABU_API_PASSWORD)
  - settings.slack_bot_token       (SLACK_BOT_TOKEN)
  - settings.slack_channel_id      (SLACK_CHANNEL_ID)
- システム環境:
  - settings.env returns one of: development, paper_trading, live（不正値は例外）
  - settings.log_level は LOG_LEVEL（大文字）を検証

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                               — ニュースセンチメント解析（OpenAI）
    - regime_detector.py                        — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                         — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                               — ETL パイプライン（run_daily_etl 等）
    - etl.py                                    — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py                          — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py                     — マーケットカレンダー管理 / 営業日判定
    - quality.py                                 — データ品質チェック
    - stats.py                                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                                   — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                         — Momentum / Value / Volatility 等
    - feature_exploration.py                      — 将来リターン / IC / 統計サマリー
  - ai/ (上記)
  - research/ (上記)

各モジュールはドキュメント文字列に処理フロー・設計方針が記載されているため、実装の意図を追いやすく保守しやすい構成になっています。

---

## テスト / モックのヒント

- OpenAI 呼び出しやネットワーク I/O は各モジュールで差し替えやすく設計されています。例えば news_nlp._call_openai_api、regime_detector._call_openai_api、news_collector._urlopen などを unittest.mock.patch でモックできます。
- 自動 .env ロードをテストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 注意事項 / ベストプラクティス

- OpenAI の呼び出しはコストとレート制限があるため、本番運用ではバッチ化やキャッシュを検討してください（実装はチャンク処理・リトライ・Backoff を備えています）。
- DuckDB への大量 INSERT は executemany とトランザクションでまとめて行っているため、ファイルサイズ・I/O に注意してください。
- run_daily_etl は市場カレンダーを先に更新してから株価/財務を取得するため、カレンダーの先読み設定（lookahead_days）を調整することで営業日の補正が可能です。
- 本ライブラリはバックテスト用のルックアヘッドバイアス防止（target_date 未満を使用する等）を意識して実装されています。バックテストで使用するときはドキュメントの注意に従ってください。

---

必要に応じて README に追加したい項目（例: CI・デプロイ手順、詳細な API 使用例、サンプル .env.example）を教えてください。