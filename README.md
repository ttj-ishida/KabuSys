# KabuSys

KabuSys は日本株向けのデータ基盤・調査・AI支援・監査ログを備えた自動売買支援ライブラリです。J-Quants API や RSS、OpenAI（LLM）を活用してデータ取得・品質チェック・ニュースセンチメント・市場レジーム判定・ファクター計算・監査ログ初期化などの機能を提供します。

---

## 主要な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合のチェック（quality モジュール）
- AI（LLM）を用いた解析
  - ニュースに基づく銘柄毎センチメント算出（news_nlp.score_news）
  - ETF（1321）MA200 とマクロニュースを合成した市場レジーム判定（regime_detector.score_regime）
- ファクター計算 / リサーチ
  - Momentum / Volatility / Value 等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル作成・初期化ユーティリティ（audit）
- ユーティリティ
  - クロスセクション Z スコア正規化、マーケットカレンダー管理、ETL 結果データクラス など

---

## 要求環境（推奨）

- Python 3.10+
- 外部ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API, OpenAI, RSS ソース など）

（実プロジェクトでは pip の依存ファイル requirements.txt / pyproject.toml を確認してください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。

4. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に必要な設定を記述できます。
   - 自動読み込みはデフォルトで有効。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

必須の環境変数（少なくとも以下は設定が必要です）:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN：Slack 通知を使う場合
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID
- KABU_API_PASSWORD：kabuステーション API を使う場合
- OPENAI_API_KEY：OpenAI を利用する場合（score_news / score_regime で利用）

その他のオプション（デフォルトあり）:
- KABUSYS_ENV：development / paper_trading / live（デフォルト development）
- LOG_LEVEL：DEBUG / INFO / ...（デフォルト INFO）
- DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH（デフォルト `data/monitoring.db`）
- PID_FILE_PATH（デフォルト `data/execution.pid`）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

---

## 使い方（簡単な例）

パッケージは Python モジュールとして利用します。以下は代表的な呼び出し例です。

- 設定参照（settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作って日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーは env または引数で指定可能）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を利用
  print("書き込み件数:", n_written)
  ```

- 市場レジームスコア計算
  ```python
  from kabusys.ai.regime_detector import score_regime
  n = score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

各関数は引数で API キーや接続を注入できる設計になっており、ユニットテスト用のモック差し替えがしやすくなっています。

---

## 動作設計上の重要な注意点

- ルックアヘッドバイアス防止：多くの処理（ニュースウィンドウやレジーム判定、ETL）は datetime.today()/date.today() を内部で直接参照しないよう設計されています。運用時は明示的に target_date を渡すことを推奨します。
- 冪等性：ETL / 保存関数は ON CONFLICT DO UPDATE などにより冪等に設計されています。
- API 呼び出しはリトライ・バックオフ・レート制御を備えています（J-Quants / OpenAI）。
- ニュース収集は SSRF 対策や最大応答サイズ制限を実装しています（news_collector）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（LLM）処理
    - regime_detector.py              — マクロ + MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - pipeline.py                     — ETL パイプライン（run_daily_etl など）
    - etl.py                          — ETLResult の公開
    - quality.py                      — データ品質チェック
    - news_collector.py               — RSS ニュース収集
    - calendar_management.py          — マーケットカレンダー／営業日判定
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py              — Momentum / Value / Volatility 計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ の各種ユーティリティとテスト用差替え箇所あり

---

## よくある運用フロー（例）

1. 夜間に ETL（run_daily_etl）を実行して最新の prices/financials/calendar を取得・保存
2. 品質チェックを実行し問題をアラート（Slack 連携など）
3. news_nlp.score_news を走らせて ai_scores を更新
4. research のファクター計算を行い、戦略側でシグナルを生成
5. 監査ログ（audit テーブル）へ signal/order/execution を記録して追跡可能にする

---

## 開発・テストについて

- 多くの外部 API 呼び出しは内部関数レベルで差し替え（モック）しやすい設計です（例: kabusys.ai.news_nlp._call_openai_api 等）。
- .env の自動読み込みはプロジェクトルート検出に依存するため、CI 等で再現性のある環境を整えてください。

---

## サポート / 参考

- 各モジュールの docstring に処理フローや設計方針が詳述されています。実装や挙動を理解するには該当モジュールの docstring とソースを参照してください。
- 環境変数や .env のフォーマットは config.py の _parse_env_line / Settings を参照してください。

---

README に記載してほしい追加項目（使い方の具体例、CI 設定例、依存ファイルの提示など）があれば教えてください。