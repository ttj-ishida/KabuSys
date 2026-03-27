# KabuSys

KabuSys は日本株を対象としたデータプラットフォーム兼リサーチ・自動売買支援ライブラリです。J-Quants API からのデータ取得（株価・財務・カレンダー）、ニュース収集・NLP によるセンチメントスコアリング、ファクター計算、ETL パイプライン、監査ログ（発注/約定追跡）などをワンパッケージで提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「ETL の冪等性」「外部 API のリトライ/フェイルセーフ」「DuckDB を用いた高速ローカル分析」です。

## 主な機能一覧

- 環境変数 / 設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の確認（settings オブジェクト経由）
- データ取得 / ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / カレンダー）
  - 差分取得・バックフィル含む日次 ETL パイプライン（run_daily_etl）
  - DuckDB への冪等保存（ON CONFLICT で上書き）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理
  - 営業日判定・前後営業日の検索・カレンダー更新ジョブ
- ニュース収集 / NLP（OpenAI）
  - RSS 取得・前処理・raw_news への冪等保存
  - ニュース銘柄別センチメント（gpt-4o-mini を利用する JSON Mode）
  - マクロニュースを使った市場レジーム判定（ETF 1321 + LLM 値を合成）
- リサーチ機能
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル定義
  - 監査用 DuckDB 初期化ユーティリティ（init_audit_db / init_audit_schema）
- セキュリティ・堅牢性
  - RSS の SSRF 対策、受信サイズ上限、defusedxml を用いた XML パース
  - API 呼び出しのリトライ・レート制御・トークン自動リフレッシュ

---

## セットアップ手順（開発環境 / 実行環境）

前提
- Python 3.10 以上（PEP 604 のユニオン型などを使用しているため）
- Git（リポジトリをクローンする場合）

1. リポジトリをクローン（既にコードがローカルにある場合は不要）
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境の作成と有効化
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

3. 依存パッケージのインストール
   - 必須パッケージ（最小例）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実運用や追加機能で別パッケージが必要になることがあります（例: Slack 通知実装等）。プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
     - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定）
     - SLACK_BOT_TOKEN: （Slack 通知を使う場合）Bot トークン
     - SLACK_CHANNEL_ID: （Slack 通知を使う場合）送信先チャネル ID
     - KABU_API_PASSWORD: kabu API 用パスワード（kabu 接続を使う場合）
   - 任意（デフォルトあり）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/…、デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易サンプル）

以下は主要ユーティリティの呼び出し例です。実行前に環境変数を設定してください。

- DuckDB 接続（例: ETL / analysis 共通）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（J-Quants から差分取得して保存、品質チェックを実行）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI）で銘柄別スコアを生成
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
  print(f"書き込み銘柄数: {written}")
  ```

- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算 / リサーチ関数
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（発注/約定トレース用）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以降 audit_conn を用いて監査テーブルへアクセス
  ```

注意点:
- AI（OpenAI）を呼び出す関数はネットワークエラーやレート制限を考慮したリトライとフェイルセーフ（エラー時はスコアを 0 にフォールバックなど）を備えていますが、API キーやコストに注意して運用してください。
- ETL / API 呼び出しには J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）と適切な権限が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py      — ニュースの NLP スコアリング（OpenAI 経由）
    - regime_detector.py — マーケットレジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py         — ETL 管理（run_daily_etl 等）
    - etl.py              — ETL の公開型（ETLResult の再エクスポート）
    - news_collector.py   — RSS 取得 / 前処理 / 保存ロジック
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            — 汎用統計（zscore_normalize 等）
    - audit.py            — 監査ログスキーマ & 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ等

---

## 開発・テストに関する補足

- 自動で .env を読み込む仕様は、テスト時に影響を与える場合があります。自動読み込みを無効にするには環境変数を設定します:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワークリクエストは関数単位で差し替え（モック）しやすいよう設計されています（テスト時は内部の _call_openai_api / _urlopen 等をパッチ）。
- DuckDB を用いるため、データ量が多い処理でもローカルで効率よく計算可能です。ETL は冪等に実装されているため、部分実行や再実行が安全です。

---

## ライセンス・貢献

この README ではライセンス情報やコントリビューション手順は明示していません。リポジトリに LICENSE / CONTRIBUTING.md がある場合はそちらを参照してください。

---

以上が KabuSys の概要と基本的な使い方です。必要であれば、各モジュール（ETL、news_nlp、jquants_client、quality など）のより詳しい使用例や API ドキュメントを追記しますので、知りたい箇所を指定してください。