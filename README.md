# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど、バックテスト / 運用に必要な機能をモジュール化しています。

バージョン: 0.1.0

---

## 主要機能（ハイライト）

- データ収集・ETL
  - J-Quants API を用いた株価（日次）・財務データ・市場カレンダーの差分取得（ページネーション・レート制御・トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、前処理（URL除去・空白正規化）
  - raw_news / news_symbols への冪等登録ロジック

- ニュースNLP（OpenAI）
  - 銘柄ごとの記事をまとめて LLM（gpt-4o-mini）に投げ、銘柄別センチメント（ai_score）を ai_scores テーブルへ保存
  - API リトライ・レスポンス検証・スコアクリッピング等の安全対策

- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）
  - Look-ahead バイアス防止の設計

- 研究用ユーティリティ（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付整合性チェックを実施し QualityIssue を返す

- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを担保するテーブル定義と初期化ユーティリティ（DuckDB）

---

## セットアップ手順

前提: Python 3.9+（typing 型ヒントでの union 型などを利用しているため）を推奨します。

1. リポジトリをクローン（既にコードがある場合はこのステップ不要）

2. 仮想環境の作成・有効化（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージインストール
   - 開発環境へインストール（editable）
     ```
     pip install -e .
     ```
   - 依存ライブラリ（主要なもの）
     ```
     pip install duckdb openai defusedxml
     ```
     ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存が記載されている想定です。必要に応じて追記してください。

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

5. DuckDB データベース作成用ディレクトリ（必要に応じて）
   - デフォルトでは data/kabusys.duckdb が使用されます。親ディレクトリがなければ自動作成されるユーティリティもありますが、手動でディレクトリを作る場合:
     ```
     mkdir -p data
     ```

---

## 必要な主な環境変数

以下は本コードベースで参照される主要な環境変数と説明（デフォルトがあるものは併記）。

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン

- OpenAI
  - OPENAI_API_KEY (必須または関数引数で注入): OpenAI API キー（score_news / score_regime 等で使用）

- kabuステーション（発注などの外部統合）
  - KABU_API_PASSWORD (必須): kabu API のパスワード
  - KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- データベース / ファイルパス
  - DUCKDB_PATH (任意): デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH (任意): デフォルト "data/monitoring.db"

- 監視 / プロセス管理
  - PID_FILE_PATH (任意): デフォルト "data/execution.pid"
  - KILL_FLAG_PATH (任意): デフォルト "data/kill.flag"
  - KILL_FLAG_CLEAR_ON_START (任意): "1" にすると起動時に kill flag をクリア

- リソース閾値（任意）
  - CPU_THRESHOLD_PCT: デフォルト 90.0
  - MEMORY_THRESHOLD_PCT: デフォルト 85.0
  - DISK_THRESHOLD_PCT: デフォルト 90.0

- 環境 / ログ
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）

.env の書式はシェルの export 付き行やクォートを含む値にも対応するパーサを持ちます。`.env.example` を参照して `.env` を作成してください（未設定の必須変数は起動時に ValueError を投げます）。

---

## 使い方（主要ユースケースの例）

以下はライブラリをプログラム的に利用する簡単な例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取ります。

- DuckDB 接続の作成（デフォルトパスを settings から取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対する銘柄別スコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY を使うか引数で渡す）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB 初期化（別ファイルで監査DBを用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出し周りはAPI失敗時にフェイルセーフ（スコア=0）にフォールバックする設計ですが、APIキーが未設定だと ValueError を出します。
- DuckDB 操作時のトランザクションとエラーハンドリングは各関数で適切に行われます（多くは BEGIN / DELETE / INSERT / COMMIT パターン）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須変数チェック）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの銘柄別センチメントスコア化（OpenAI）
    - regime_detector.py
      - ETF 乖離 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
      - ETLResult データクラス（結果 & 品質問題の集約）
    - jquants_client.py
      - J-Quants API クライアント（取得/保存/認証/レート管理）
    - news_collector.py
      - RSS フィード取得、記事前処理、raw_news 登録
    - calendar_management.py
      - JPX カレンダー管理（営業日判定 / calendar_update_job）
    - audit.py
      - 監査ログテーブルのDDL・初期化ユーティリティ
    - etl.py
      - ETLResult のエクスポートインターフェース
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、ランク関数
  - monitoring, strategy, execution, ... (パッケージ公開名に含まれるが今回のコード抜粋に応じて実装あり/なし)

（上記は主要ファイルの要約です。個別の関数・クラスは各ソースの docstring を参照してください。）

---

## 設計方針・注意事項（短く）

- Look-ahead バイアス回避が至上命題:
  - 日時の計算は target_date を受け、datetime.today() の直接参照を避ける設計が多く採用されています。
- 冪等性重視:
  - DB への保存は可能な限り ON CONFLICT / DELETE→INSERT のパターンで既存データ保護。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants 等）失敗時もシステム全体を止めないように設計（ログ・スキップ・デフォルト値を採用）。
- テスト容易性:
  - 外部呼び出しを抽象化・モックしやすい構造（_call_openai_api の差し替え等）。

---

## さらに読む / 今後の拡張案

- CLI やサービス起動用のエントリポイント（systemd / supervisor 用の起動スクリプト）
- 詳細な要求に合わせた発注モジュール（kabu ステーション連携の実装）
- 性能監視・メトリクス（Prometheus など）や実運用向けの監視アラート統合
- テスト用の fixtures / CI 設定（OpenAI・J-Quants クライアントのモック）

---

ご要望があれば、README に CI 設定例、requirements.txt、または具体的な運用手順（cron / container / systemd）を追加して展開します。どの部分を詳細化しましょうか？