# KabuSys

KabuSys は日本株のデータプラットフォーム、リサーチ、AI を組み合わせた自動売買支援ライブラリです。  
DuckDB を用いたデータ格納／ETL、J-Quants API 経由の市況／財務データ取得、RSS ベースのニュース収集、OpenAI を用いたニュース NLP、研究用のファクター計算・特徴量解析、監査ログ（発注／約定トレース）などを提供します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応、ID トークン自動リフレッシュ、レートリミット管理
- ニュース収集
  - RSS フィード収集、URL 正規化、トラッキングパラメータ除去、SSRF 対策、raw_news / news_symbols 保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントスコア（ai_scores）算出（gpt-4o-mini を利用）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用途ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化、統計サマリー
- データ品質チェック
  - 欠損値・スパイク・重複・日付整合性の検出（QualityIssue で集約）
- 監査ログ（Audit）
  - signal_events / order_requests / executions など、シグナルから約定までトレース可能な監査スキーマの初期化と管理
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルート検出）と安全な必須チェック

---

## セットアップ手順（開発者向け）

前提: Python 3.10+ を想定しています。環境に合わせて適宜調整してください。

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（project の requirements ファイルがある前提。一例）
   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   # 必要に応じて他の依存を追加
   ```

   ※パッケージ化されている場合:
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（およびローカル専用の `.env.local`）を置くと、自動的に読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（README 内で参照されるもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース／監査スキーマ初期化（例）
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   import duckdb

   # 監査ログ用 DB を初期化（ファイルパスでも :memory: でも可）
   audit_conn = init_audit_db(settings.duckdb_path)  # 必要に応じ別 DB にする
   # または通常の DuckDB 接続を使ってその他スキーマ作成等を行う
   conn = duckdb.connect(str(settings.duckdb_path))
   ```

---

## 使い方（主要 API と利用例）

以下は簡単な Python からの利用例です。実行には適切な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）が必要です。

- ETL 日次実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコアリング）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で OPENAI_API_KEY を使用
  print(f"scored: {count}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- AI（OpenAI）を使う処理は API 呼び出しが発生し、利用コスト・レートリミットが発生します。テスト時は該当内部の _call_openai_api をモックできます（ユニットテストでパッチ可能）。
- J-Quants API にはレート制限があり、本ライブラリは内部でレートリミット制御とリトライを実装しています。

---

## 設計上の重要なポイント / 動作挙動

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml が見つかる場所）を基準に `.env` と `.env.local` を読み込む。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- Look-ahead bias 対策
  - AI モジュール・ETL・取得処理では現在時刻を直接参照して将来データを参照することがないよう配慮（target_date を引数で与える設計）。
  - J-Quants の取得では fetched_at を UTC で記録して「いつデータを取得したか」を追跡可能にしています。

- フォールバック
  - マーケットカレンダーが存在しない場合は曜日ベース（土日非営業）でフォールバックします。DB に一部しかカレンダーがない場合でも挙動が一貫するよう設計されています。

- エラーハンドリング
  - 多くの長時間実行処理（ETL・API 呼び出し）は例外発生時にロギングして処理を継続するフェイルセーフ設計。ETL 結果は ETLResult で報告されます。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理 (.env 自動ロード、Settings)
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（銘柄別スコアリング）
    - regime_detector.py             — マクロ + ma200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py                    — ETL パイプライン（run_daily_etl など）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS 収集 / 前処理 / 保存
    - calendar_management.py         — マーケットカレンダー管理（is_trading_day 等）
    - quality.py                     — データ品質チェック
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在する場合: 監視系モジュール)
  - strategy/, execution/ etc. (将来的な拡張点)

---

## テスト・開発メモ

- OpenAI 呼び出しは内部関数 `_call_openai_api` をテスト時にモックして振る舞いを制御できます（news_nlp と regime_detector で独立して定義されています）。
- DuckDB の `:memory:` を使えば単体テストでインメモリ DB として動作させられます。
- ETL 系の外部 API 呼び出し（J-Quants）はモジュール `kabusys.data.jquants_client._request` をモックすることでネットワークレスのユニットテストが可能です。

---

## トラブルシューティング（よくある問題）

- 起動時に環境変数未設定で ValueError が出る
  - Settings は必須キー（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を参照すると ValueError を出します。`.env.example` を参考に `.env` を作成してください。
- OpenAI 呼び出しで JSON パースエラーが出る
  - モデルの出力が厳密な JSON でない場合に備え、実装は復元ロジックを含みますが、不正な出力やコスト面の理由でテスト時はモック推奨です。
- J-Quants API の 401 エラー
  - `_request` は 401 の場合に自動でリフレッシュを試みますが、リフレッシュに失敗した場合は get_id_token の確認や JQUANTS_REFRESH_TOKEN の有効性を確認してください。

---

必要であれば、README に含めるコマンド例や schema 初期化/マイグレーション手順、CI 用の設定（環境変数の管理、テスト用のモックデータ準備）を追加できます。どの部分を拡張したいか教えてください。