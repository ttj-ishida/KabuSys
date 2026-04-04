# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、マーケットカレンダー等の機能を備え、バックテストや運用バッチの基盤として利用できます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score）とマクロセンチメント（市場レジーム判定）
- ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量探索ユーティリティ
- データ品質チェック、監査ログ（発注→約定のトレーサビリティ）
- DuckDB ベースでのローカル保存・冪等保存ロジック

設計上、ルックアヘッドバイアスを避ける考慮や、外部 API 呼び出しのリトライ／バックオフ、堅牢な入力検証（URL 正規化 / SSRF 対策 / JSON バリデーション）等が組み込まれています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - J-Quants API クライアント（認証・ページネーション・レート制御・再試行）
- ニュース収集
  - RSS 取得（SSRF 対策、XML 安全パーサ）
  - raw_news / news_symbols への冪等保存
- ニュースNLP（OpenAI）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores に書込
  - gpt-4o-mini（JSON Mode）利用、バッチ処理・リトライ実装
- 市場レジーム判定
  - score_regime: ETF 1321 の MA＋マクロニュースで market_regime に書込
- 研究用ユーティリティ
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン、IC 計算、Z スコア正規化 等
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue オブジェクト）
- 監査ログ
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化
- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）、環境変数経由の設定読み取り

---

## セットアップ手順

推奨: Python >= 3.10（本コードは型ヒントや union 演算子（|）を使用しています）。可能であれば 3.11 以上を推奨します。

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール（例）
   pip の要件ファイルは本コードには含まれていませんが、最低限以下をインストールしてください：
   ```
   pip install duckdb openai defusedxml
   ```
   - 実運用では logging, urllib 等の標準ライブラリ以外に、必要なパッケージを追加してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（.env.local が存在すれば上書きされます）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 必須 / 推奨環境変数

config.Settings から参照される主要な環境変数（最低限設定が必要なもの）：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_BASE_URL: kabu API のベース URL（オプション、デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視データ用 sqlite パス（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=eyJ...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=DEBUG
KABUSYS_ENV=development
```

注意: .env.local は .env を上書きするため、ローカル機密設定は .env.local に置く運用が可能です。

---

## 使い方（簡易例）

以下は主なユースケースの最小実行例です。実行前に環境変数と DuckDB ファイル（または :memory:）を準備してください。

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメント（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査専用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究用（ファクター計算 / forward returns / IC）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

  momentum = calc_momentum(conn, date(2026, 3, 20))
  fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## 注意点 / 実運用上のヒント

- OpenAI 利用
  - news_nlp と regime_detector は gpt-4o-mini を指定しています。API 呼び出しは JSON mode を使って厳密な JSON 応答を期待します。
  - API 失敗時はフォールバックの扱い（0.0）やスキップを行う設計です。運用時はレート・コスト管理に注意してください。

- Look-ahead バイアス対策
  - ほとんどの関数は datetime.today() を直接参照せず、引数で target_date を受け取って過去データのみ参照するよう設計されています。バックテスト時は必ず過去の状態に合わせてデータを準備してください。

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env / .env.local を読み込みます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- データベース互換性
  - DuckDB のバージョン依存差異（executemany の空リストなど）を考慮した実装になっていますが、使用している DuckDB バージョンとの整合性は確認してください。

---

## ディレクトリ構成（概要）

以下は主要ファイル/モジュールの一覧と概要（src/kabusys 以下）：

- __init__.py
  - パッケージのバージョンと公開サブパッケージ指定

- config.py
  - 環境変数・.env ロード / Settings クラス

- ai/
  - news_nlp.py : ニュースのセンチメント解析と ai_scores 書込ロジック
  - regime_detector.py : ETF MA とマクロニュースで市場レジーム判定
  - __init__.py

- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得／保存）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py : ETLResult 再エクスポート
  - news_collector.py : RSS 収集・前処理・保存
  - calendar_management.py : 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - quality.py : データ品質チェック
  - audit.py : 監査ログ DDL と初期化ユーティリティ
  - stats.py : Z スコア正規化 等の統計ユーティリティ

- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ算出
  - feature_exploration.py : forward returns, IC, factor_summary, rank

（各ファイルは README の上位セクションで説明した通りの役割を持ちます。）

---

## 開発・テスト時のヒント

- OpenAI や J-Quants への外部呼び出し部分はモック可能な設計になっています（内部の _call_openai_api 等を patch する等）。
- news_collector のネットワーク部分や J-Quants クライアントはリトライ・レート制御を行うため、本番 API キーを使う前に小規模で動作検証を行ってください。
- DuckDB に対する DDL/保存は冪等（ON CONFLICT）を意図していますが、スキーマ初期化やマイグレーションは別途管理してください。

---

## ライセンス / コントリビューション

（ここにプロジェクトのライセンスやコントリビューション指針を記載してください）

---

必要であれば、README に実際の requirements.txt、CI 実行例、サンプル .env.example、より具体的な CLI 実行スクリプト例を追加できます。どの情報を追加しますか？