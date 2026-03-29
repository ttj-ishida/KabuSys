# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL、ニュース収集・NLP、ファクター計算、監査（トレーサビリティ）、および市場レジーム判定など、取引システム・リサーチワークフローで利用する主要機能を提供します。

注: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。

## プロジェクト概要

KabuSys は以下の要素を中心に実装された Python モジュール群です。

- J-Quants API からのデータ取得および DuckDB への差分保存（ETL）
- RSS ニュース収集と OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースセンチメント）
- 研究用ユーティリティ（ファクター計算・特徴量探索・統計ユーティリティ）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 市場カレンダー管理（JPXカレンダーの ETL と営業日判定）

設計上の注意点（コード内に明示）:
- ルックアヘッドバイアスを避けるため、内部で datetime.today() / date.today() を直接使わない設計
- 多くの処理は DuckDB 接続を受け取り SQL と Python の組合せで実行
- 外部 API 呼び出し（J-Quants / OpenAI等）はリトライ・バックオフ・フェイルセーフを考慮

## 主な機能一覧

- data/
  - ETL パイプライン（prices / financials / market_calendar の差分取得・保存）
  - J-Quants API クライアント（取得・保存用関数、認証・レート制御・ページネーション対応）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF対策・サイズ制限・正規化）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal_events, order_requests, executions の初期化・DB操作）
  - 統計ユーティリティ（z-score 正規化 等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI に送って ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の ma200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ保存
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリー、ランク関数 等
- config.py
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を順次読み込み）
  - Settings クラスで主要設定値を取得（必須 env の確認も行う）

## 必要な環境・依存関係

主な依存（コードから明示されているもの）:
- Python 3.10+（typing の union 短縮表記などを使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他は標準ライブラリ（urllib, json, datetime, logging, math, etc.）を使用しています。

（プロジェクト配布時は requirements.txt / pyproject.toml を確認してください）

## セットアップ手順

1. リポジトリをクローン / コピー
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 代表的なパッケージ例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは pyproject.toml / requirements.txt に従ってください。

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して設定できます。自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN … J-Quants の refresh token
     - KABU_API_PASSWORD … kabuステーション API パスワード
     - SLACK_BOT_TOKEN … Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID … Slack 通知先チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV … development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL … DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL … kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH … 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - OpenAI の API キー（score_news / score_regime の引数を渡さない場合に参照）:
     - OPENAI_API_KEY … (任意) OpenAI API キー

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   KABUSYS_ENV=development
   ```

5. データベース用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

## 使い方（簡単なコード例）

以下は最小限の利用例です。各関数は DuckDB の接続オブジェクトを受け取ります。

- DuckDB 接続を作成する
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（prices / financials / calendar を差分取得、品質チェック含む）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))  # 書き込んだ銘柄数を返す
  print("written:", written)
  ```

- 市場レジーム判定（ETF 1321 の ma200 とマクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用 DB 初期化（監査専用の DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しはネットワーク・API レートの影響を受けるため、API キーや使用量に注意してください。
- ETL / ニュース収集 / AI 呼び出しにはそれぞれエラーハンドリングやリトライロジックが組み込まれていますが、運用時はログと監視を必ず行ってください。

## 設定・動作に関する補足

- 環境変数の自動読み込み:
  - パッケージ import 時に、プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を順に読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- Settings クラス:
  - settings.is_live / is_paper / is_dev で実行環境判定が可能です。
  - 必須 env が未設定の場合、Settings の該当プロパティ呼出しで ValueError が発生します。
- エラー・フェイルセーフ:
  - OpenAI / J-Quants クライアントはリトライとフェイルセーフ（失敗時に 0.0 スコア等で継続）を備えていますが、致命的な DB 書き込み失敗などは例外が上位に伝播します。

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル一覧（今回のコードベースから抽出）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - (その他: etl で再エクスポートされる型など)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割は前節の「主な機能一覧」を参照してください。

## ログと監視

- ログレベルは環境変数 `LOG_LEVEL` で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ETL の結果は ETLResult クラス（kabusys.data.pipeline.ETLResult）で返され、to_dict() で要約情報を取得できます。
- データ品質チェックは quality.run_all_checks を使って個別または一括で実行できます。

## ライセンス・貢献

この README はソースコードから自動生成した説明を含みます。実際のライセンスやコントリビュート手順はリポジトリのルートにある LICENSE / CONTRIBUTING 文書を参照してください。

---

以上が KabuSys の基本的な README です。利用や運用に際して具体的な拡張・運用手順（ジョブスケジューラ設定、Slack 通知フロー、kabuステーションとの連携）は別途ドキュメント化することを推奨します。必要であれば使用例やデプロイ手順、CI テストの記述も作成します。どの部分を詳述しましょうか？