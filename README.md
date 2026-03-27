# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、ETL、品質チェック、監査ログなど、バックテスト・実運用で必要となる機能群を提供します。

## 主な特徴（機能一覧）
- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可）
  - 必須環境変数チェック（未設定時は ValueError）
- データ取得 / ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集・NLP
  - RSS 取得（SSRF対策、gzip上限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント解析（ai_scores）
  - レスポンス検証・バッチ処理・リトライ付き
- 市場レジーム判定
  - ETF(1321) の 200 日MA乖離 + マクロニュースLLMセンチメントを合成して日次で bull/neutral/bear を判定
  - LLM 呼び出し失敗時はフェイルセーフ（マクロ寄与=0)
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合検出
  - QualityIssue オブジェクトで詳細を返す
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 発注の冪等性確保（order_request_id）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

2. 必要なパッケージをインストール  
   本コードで想定される主要依存：
   - duckdb
   - openai
   - defusedxml
   例（pip）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements.txt / pyproject.toml があればそちらに従ってください。

3. パッケージをインストール（開発モード）
   ```bash
   pip install -e .
   ```
   （パッケージ配布方式に合わせて適宜）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（モジュール import 時に自動ロード）。
   - 自動ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 最低限必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
     - KABU_API_PASSWORD: kabuステーション API パスワード（約定等の外部モジュールがあれば）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - DUCKDB_PATH / SQLITE_PATH: ローカル DB パス（省略時は data/ 以下に配置）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=yourpassword
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は代表的なモジュールの使い方例です。実行は仮想環境内で行ってください。

- DuckDB 接続の作成（デフォルトファイルは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次パイプライン）の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定、省略時は today が使われます
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API を使用）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ma200 と マクロニュース合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ DB の初期化（専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが必要な接続にDDL を適用済み
  ```

- 研究系ユーティリティ（ファクター計算）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  ```

エラーメッセージ:
- 設定されていない必須環境変数は Settings プロパティからアクセスすると ValueError を投げます（例: settings.jquants_refresh_token）。
- OpenAI 呼び出しや J-Quants API 呼び出しはリトライ・フォールバック実装がありますが、API キー不在などは明確な例外になります。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動ロード、Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースの OpenAI スコアリング、score_news
  - regime_detector.py — 市場レジーム判定、score_regime
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、fetch/save 系
  - pipeline.py — ETL パイプライン run_daily_etl 等、ETLResult
  - etl.py — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- research/ 以下は研究用ユーティリティ群

その他:
- data/ (実行時のデータ置き場、デフォルト DUCKDB_PATH は data/kabusys.duckdb)
- .env.example（プロジェクトルートに置かれる想定。設定例を参照）

---

## 注意・運用上のポイント
- Look-ahead バイアス回避設計が各所に組み込まれています（datetime.today() を直接参照しない等）。バッチやバックテストでの使用方法に注意してください。
- 自動で .env を読み込む際はプロジェクトルートの検出に .git または pyproject.toml を使用します。パッケージ配布後やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI の呼び出しはコストがかかります。ローカルテストではモック差し替え（unittest.mock.patch）を推奨します（モジュール内の _call_openai_api を差し替え可能）。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン依存の扱いに配慮している箇所があります（空チェックに注意）。

---

## トラブルシューティング（簡易）
- ValueError: 環境変数が未設定 → .env を作成して必須キーを設定してください。
- API 呼び出し系のタイムアウトやネットワークエラー → 一時的な問題の可能性、ログを確認し再試行してください。J-Quants / OpenAI はリトライ実装あり。
- DuckDB にスキーマがない → audit.init_audit_db や既存のスキーマ初期化ユーティリティを使用してテーブルを作成してください。

---

必要に応じて README にコマンド例や CI／デプロイ手順（systemd / cron / Airflow 等でのスケジューリング）、詳細な .env.example を追加できます。追加したいセクションがあれば教えてください。