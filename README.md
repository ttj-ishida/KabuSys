# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせて、データ収集（ETL）・品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログ（トレーサビリティ）を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）
  - 差分取得・バックフィル・ページネーション対応・トークン自動リフレッシュ
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、主キー重複、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約
- ニュース収集 / NLP
  - RSS からニュースを収集し raw_news に保存（SSRF対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（ai_scores）を生成
  - レート制限・リトライ・バッチ処理対応
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）判定
  - LLM 呼び出しにはフォールバック／リトライを実装
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化するユーティリティ（DuckDB）
  - UUID ベースのトレーサビリティ設計、created_at / updated_at の扱いを保証

---

## セットアップ手順

前提:
- Python 3.10+（type union 表記などを利用）
- ネットワーク接続（J-Quants / OpenAI 等にアクセス可能であること）
- DuckDB（Pythonパッケージとしてインストールされます）

1. リポジトリを取得（例）
   ```bash
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. インストール（pip）
   プロジェクトの packaging が無い場合は必要なパッケージを直接インストールしてください。主な依存例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   開発用に他パッケージがあれば pyproject.toml / requirements.txt に従ってください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を探索）に配置した `.env` / `.env.local` が自動で読み込まれます（起動時の環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須（少なくとも動作に必要なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知を使う場合
   - KABU_API_PASSWORD — kabuステーション API のパスワード（必要時）
   - OPENAI_API_KEY — OpenAI を使う機能を利用する場合

   任意（デフォルト値あり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 sqlite（デフォルト data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な API / 実行例）

このパッケージはライブラリとしてインポートして使用します。以下は代表的な利用例です。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 株価（prices）だけの差分 ETL を実行
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュース NLP（銘柄別センチメント）を実行
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))  # 戻り値は書き込んだ銘柄数
  ```

  注意: OpenAI API キーは `OPENAI_API_KEY` 環境変数か、`api_key` 引数で渡してください。API 呼び出しは gpt-4o-mini を想定しています。

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ（audit）DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ用ファクター計算例
  ```python
  from kabusys.research import calc_momentum, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 環境変数自動ロード
  - パッケージ読み込み時にプロジェクトルートの `.env` → `.env.local` の順で自動ロードします（既存 OS 環境変数は保護）。
  - 自動ロードを無効にする場合:
    ```bash
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## 実運用上の注意 / ベストプラクティス

- OpenAI / J-Quants は外部ネットワーク API のため、APIキーの管理・レート制限・課金に注意してください。
- ETL は差分取得・バックフィルロジックを持つため、バックテスト時のルックアヘッドバイアスに注意して利用してください（関数は明示的に date を受け取り、内部で datetime.today() を参照しない設計）。
- ニュース収集では SSRF 対策・受信サイズ制限・XML パースの安全対策（defusedxml）を実装していますが、運用環境のログや例外に注意してください。
- DuckDB の executemany に関する注意点（空リスト不可）など実装上の制約があるため、API 呼び出しの戻り値チェックを行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の概要です。

- kabusys/
  - __init__.py — パッケージエントリ（version 等）
  - config.py — 環境変数 / 設定管理（自動 .env ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI）で ai_scores へ保存する処理
    - regime_detector.py — 市場レジーム判定（MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の再公開
    - calendar_management.py — マーケットカレンダー判定・update ジョブ
    - news_collector.py — RSS 取得・前処理・保存
    - quality.py — データ品質チェック
    - stats.py — 共通統計ユーティリティ（zscore）
    - audit.py — 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — forward returns, IC, rank, factor_summary
  - monitoring/ (未表示ファイルだが存在想定) — 実行プロセス監視や Slack 通知等

（コードベースの一部ファイルのみ抜粋しています。詳細はソースを参照してください）

---

## よくある質問（FAQ）

- Q: OpenAI API のレスポンスが不正だった場合はどうなる？
  - A: news_nlp/regime_detector ではパース失敗や API エラー時にフォールバック（0.0）や空スコアで処理を継続し、致命的な例外にはしない設計です。ログを確認してください。
- Q: .env が自動で読み込まれません
  - A: パッケージは __file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索します。プロジェクトルートに配置されていること、あるいは KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないことを確認してください。
- Q: DuckDB のスキーマはどこで作成する？
  - A: 各 ETL / save_* 関数は前提のテーブルが存在することを期待します。スキーマ初期化用のユーティリティ（data.schema 等）がある場合はそれを実行するか、DDL を事前に準備してください。監査ログは data.audit.init_audit_db で初期化できます。

---

## 貢献 / 開発

- Lint / type check を通すこと（静的解析やテストの追加が望ましい）
- API 呼び出し部分（OpenAI / J-Quants）はモック可能に実装済み（テスト時に patch で差し替え）
- 変更を加える際は Look-ahead Bias や冪等性の設計原則を尊重してください

---

問題や機能追加の提案があれば README を更新するか、issue を立ててください。