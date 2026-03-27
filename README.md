# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants、RSS）、ETL パイプライン、データ品質チェック、AI を使ったニュースセンチメント解析・市場レジーム判定、ファクター計算、監査ログ（発注トレーサビリティ）など、バックテスト・運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能一覧

- データ収集・ETL
  - J-Quants API からの株価日足・財務データ・マーケットカレンダー取得（ページネーション、レート制御、再試行、トークン自動リフレッシュ）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols テーブルへの冪等保存
- AI（OpenAI）
  - ニュースセンチメント解析（gpt-4o-mini を使用、JSON Mode 想定） — kabusys.ai.news_nlp.score_news
  - マクロ + テクニカルを組み合わせた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース） — kabusys.ai.regime_detector.score_regime
- 研究・ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化ユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などの検出（QualityIssue を返す）
- 市場カレンダー管理
  - JPX カレンダーの差分取得、営業日判定/前後営業日取得など
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（冪等）
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（自動ロード可／無効化可）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（ソースで | 型注釈を利用）
- 必要な外部依存（代表例）:
  - duckdb
  - openai
  - defusedxml

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. パッケージをインストール
   - setup.py / pyproject.toml がある場合は開発インストール:
     ```bash
     pip install -e .
     ```
   - あるいは最低限の依存を手動で:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   プロジェクトルートの `.env` / `.env.local` を使うか、OS 環境変数として以下を設定します。サンプル（.env.example を参考に作成してください）。

   必須（このプロジェクト内で使用している設定）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合のボットトークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネルID
   - KABU_API_PASSWORD     : kabu ステーション等を使う際の API パスワード（必要な場合）
   - OPENAI_API_KEY        : OpenAI を使う機能を利用する場合（score_news, score_regime 等）

   任意/デフォルトあり:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB 等（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   自動 .env 読み込みを無効化する場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化（監査用の例）
   Python から監査用 DB を初期化できます:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn を使って追加処理が可能
   ```

---

## 使い方（主要な API と実行例）

以下は代表的な機能の呼び出し例です。各関数はプログラム（ジョブ）から直接呼び出して利用する想定です。

- DuckDB 接続の作成（ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- J-Quants の日足を手動で取得・保存
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュースセンチメント解析（ai.news_nlp）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # score_news は OpenAI API key を env OPENAI_API_KEY で参照するか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み件数:", written)
  ```

- 市場レジーム判定（ai.regime_detector）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  ret = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログテーブルの初期化（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 市場カレンダーの判定ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- AI（OpenAI）を呼ぶ関数はネットワーク呼び出しを行い、レスポンスの形式や API のレートに依存します。テスト時は該当モジュール内の _call_openai_api をモックして差し替える設計になっています。
- DB 書き込みは多くが冪等（ON CONFLICT ... DO UPDATE）で実装されていますが、運用時はバックアップ・監査を忘れないでください。

---

## 環境変数 / 設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (必要に応じて): OpenAI API キー（score_news / score_regime 等）
- KABU_API_PASSWORD (必須 for kabu API): kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 if Slack notifications used)
- SLACK_CHANNEL_ID (必須 if Slack notifications used)
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: ログレベル（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

環境変数は .env/.env.local または OS 環境変数で提供してください。パスワードやトークンはソース管理にコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュール構成（src/kabusys 以下）です。抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント解析（OpenAI）
    - regime_detector.py           -- MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult の公開
    - news_collector.py            -- RSS 取得・正規化・保存
    - calendar_management.py       -- 市場カレンダー管理 / 営業日判定
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- Momentum / Volatility / Value 等
    - feature_exploration.py       -- forward returns, IC, summary, rank
  - (その他)
    - strategy/                     -- 戦略関連（エントリポイント等が想定）
    - execution/                    -- 発注 / ブローカー連携
    - monitoring/                   -- 監視 / アラート関連

（実際のリポジトリには strategy / execution / monitoring の実装ファイルが含まれる想定です）

---

## 開発・テスト時のヒント

- テストで環境変数自動ロードを無効にする:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI や J-Quants 呼び出しは外部サービスに依存するため、ユニットテストではネットワーク呼び出しをモックしてください。モジュール内で置換可能な小さなラッパー関数（_call_openai_api など）を提供している箇所があります。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性に配慮している箇所があります。テスト時に空パラメータを渡さないよう注意してください。

---

## ライセンス / 注意事項

- API キー・シークレットは漏洩しないように管理してください。
- 実運用で発注ロジックを組み合わせる際には十分なリスク管理とテストを行ってください（本ライブラリはあくまで基盤を提供します）。
- 各種外部 API（J-Quants / OpenAI / 証券会社 API 等）の利用規約・レートリミットに従ってください。

---

質問や追加したいドキュメント（設計書や運用ガイド等）があれば教えてください。README の改善・日本語表現の調整も対応します。