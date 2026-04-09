# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレーサビリティ）など、マーケットデータ基盤とリサーチ／シグナル生成に必要な機能を含みます。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（OHLCV）/ 財務 / 上場情報 / 市場カレンダー取得（ページネーション・自動リトライ・レート制御）
  - 差分取得・バックフィル・冪等保存（DuckDB へ ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（pipeline.run_daily_etl）
- データ品質管理
  - 欠損、スパイク、重複、日付不整合などのチェック（quality モジュール）
- カレンダー管理
  - JPX カレンダー管理、営業日判定、next/prev trading day 取得（calendar_management）
- ニュース収集・前処理
  - RSS からのニュース取得、URL 正規化、SSRF 防止、テキスト前処理、raw_news への冪等保存（news_collector）
- AI（LLM）によるスコアリング
  - ニュース -> 銘柄センチメント（ai.news_nlp.score_news）
  - マクロセンチメント + MA 指標を合成して市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI API（gpt-4o-mini）を JSON mode で利用、リトライとフォールバック実装あり
- 研究用ユーティリティ
  - モメンタム/バリュー/ボラティリティ等のファクター計算（research）
  - 将来リターン計算、IC 計算、Zスコア正規化（data.stats / research）
- 監査・トレーサビリティ
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（data.audit）
  - 監査DBの初期化関数（init_audit_db）

---

## 動作要件（推奨）

- Python 3.10 以上（型注釈で `X | None` を使用しているため）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を利用する場合）
- defusedxml（RSS パースの安全対策）
- ネットワーク接続（J-Quants / OpenAI / ニュース RSS）

必須パッケージ（例）
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要ライブラリをインストール
   （requirements.txt が無い場合は個別に）
   ```bash
   pip install duckdb openai defusedxml
   # 他に必要なパッケージがあればここで追加
   ```

3. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます（os 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（一例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxx         # 必須（J-Quants）
   OPENAI_API_KEY=sk-xxxxxx              # OpenAI を使う場合は必須
   KABU_API_PASSWORD=your_password       # kabuステーション連携がある場合
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト
   LINE_CHANNEL_ACCESS_TOKEN=            # 通知等に使用（任意）
   LINE_USER_ID=                          # 任意
   DUCKDB_PATH=data/kabusys.duckdb       # デフォルトパス
   SQLITE_PATH=data/monitoring.db
   PAPER_FILL_MODE=instant               # instant|partial|never|reject
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   KABUSYS_ENV=development               # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は最小の使用例です。DuckDB 接続を作成して ETL を実行したり、AI スコアを計算できます。

- 日次 ETL の実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定しなければ今日（settings.env で調整）
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごとの ai_scores へ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  cnt = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
  print(f"書き込んだ銘柄数: {cnt}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # settings.sqlite_path などを監査DBに使うことが多いです
  conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  ```

- 研究用関数例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(mom[:5])
  ```

注意点:
- OpenAI / J-Quants の API キーは環境変数または関数引数で渡します。関数は環境変数が未設定の場合に ValueError を投げます。
- LLM 呼び出しは失敗した場合にフォールバック（0.0）することが多く、処理全体を停止しない設計です。

---

## 設定と自動読み込みの挙動

- .env / .env.local はプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みされます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - 既存の OS 環境変数は保護されます（.env で上書きされない）
- 自動読み込みを無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- 必須のキー:
  - JQUANTS_REFRESH_TOKEN（ETL/J-Quants を使う場合）
  - OPENAI_API_KEY（AI スコアリングを行う場合）
  - KABU_API_PASSWORD（kabu ステーション連携がある場合）

---

## 主要モジュールとディレクトリ構成

簡易ツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースから銘柄ごとのスコアを生成
    - regime_detector.py           — マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETLResult エクスポート
    - calendar_management.py       — 市場カレンダー管理・営業時間判定
    - news_collector.py            — RSS 取得・前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（z-score 等）
    - audit.py                     — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility 等
    - feature_exploration.py       — 将来リターン計算・IC・summary 等
  - ai/, data/, research/ の他に strategy/, execution/, monitoring などが想定されている（パッケージ公開用 __all__ に記載）

---

## 開発 / テストのヒント

- DuckDB のファイルパスは Settings.duckdb_path（デフォルト: data/kabusys.duckdb）で管理されています。テストでは ":memory:" を使うと便利です。
- ai モジュールの OpenAI 呼び出し箇所はテストしやすいように内部呼び出し（_call_openai_api）をモックできます。
- .env.example を参考に .env を作成してください（リポジトリに例が含まれる想定）。

---

## 参考 / 注意事項

- LLM を利用するコードは API レートや費用の観点から運用上の配慮が必要です（バッチサイズ / リトライ / フォールバック設計済み）。
- ETL・品質チェックは DB に影響を与えるため、本番データベースで実行する場合は事前にバックアップを取ることを推奨します。
- この README はコードベースの抜粋に基づく概要です。実運用前に各関数のドキュメントと実装を確認してください。

---

質問や README の追加項目（例: API レート制御、モニタリング・アラート連携、Docker 化手順など）が必要であれば教えてください。必要に応じて追記します。