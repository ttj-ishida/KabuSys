# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
J-Quants からのデータ取得・ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ／発注トレースなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスに配慮した時系列処理（内部で date.today()/datetime.today() に直接依存しない実装）
- DuckDB をデータ格納基盤として使用（軽量かつ SQL ベース）
- J-Quants / OpenAI 等の外部 API はリトライ・レート制御・フェイルセーフを実装
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替可能

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`、自動ロードは環境変数で無効化可能）
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得 & DuckDB への冪等保存
  - 財務データ取得 & 保存
  - JPX マーケットカレンダーの取得・保存
  - 日次一括 ETL 実行（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集
  - RSS フィード収集、安全対策（SSRF 除去・gzip 上限・XML サニタイズ等）と raw_news テーブル保存
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを集約して LLM に投げ、センチメント（ai_score）を ai_scores テーブルへ保存
  - チャンク・バッチ処理、レスポンス検証、リトライを実装
- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを組み合わせて日次レジームを算出・保存
- 研究用ユーティリティ（research）
  - Momentum/Volatility/Value 等のファクター計算
  - 将来リターン・IC（Information Coefficient）・統計サマリ等
- 監査ログ／トレーサビリティ（audit）
  - signal_events / order_requests / executions テーブルの初期化＆管理
  - 発注〜約定までの UUID ベースのトレースを想定

---

## 前提・依存関係

最低限の想定依存パッケージ（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）：
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ: urllib, json, logging 等）

注意：OpenAI や J-Quants の API は有料・レート制限があるため、キーの管理や呼び出し頻度に注意してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone … && cd kabusys

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに pyproject.toml がある場合: pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に環境変数から参照）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - 例 `.env`（最小）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C0123456789
     KABU_API_PASSWORD=your_kabu_password
     ```

5. データベース初期化（監査ログ用）※任意だが推奨
   - Python から:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
     ```
   - あるいは既存の DuckDB コネクションに対して init_audit_schema を呼ぶことも可能です。

---

## 使い方（主な API と実行例）

以下はライブラリを利用する際の代表的なコード例です。適宜ログ設定やエラーハンドリングを追加してください。

- DuckDB 接続の例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア算出（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存コネクションに対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算の例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  factors = calc_momentum(conn, target_date=date(2026, 3, 20))
  # factors は [{'date': ..., 'code': '1301', 'mom_1m': ..., ...}, ...]
  ```

注意点：
- score_news / score_regime は OpenAI API 呼び出しを行うため、API キーとコスト、レート制限に注意してください。
- 本ライブラリには実際の注文送信（ブローカー API に対する発注ラッパー）は含まれていないか、別モジュール（execution など）で実装する想定です。運用時は安全対策（ペーパートレードの検証、二重発注防止、監査ログの確認）を必ず行ってください。
- 環境が `live`（KABUSYS_ENV=live）の場合は実行時の挙動や通知等で取り扱いに注意してください（誤発注リスク）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必要に応じて) — OpenAI 呼び出しに使用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to 1 to disable automatic .env loading (useful for tests)

---

## ディレクトリ構成

主要なファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境設定・.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL インターフェース再エクスポート
    - news_collector.py — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ初期化 / schema 管理
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - (その他) strategy/, execution/, monitoring/（パッケージのエクスポート想定）

---

## 開発・テストメモ

- 自動 .env 読み込みを無効化してユニットテストを実行したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 HTTP はユニットテストでモック可能なように実装されています（内部呼び出しを patch する等）。
- DuckDB を使うため、テストでは ":memory:" をパスとして渡すことでインメモリ DB を使用できます。

---

## 補足・運用上の注意

- 外部 API（J-Quants、OpenAI、kabuステーション）はレート制限・認証・課金ポリシーがあるため、本番環境での運用前に十分な検証を行ってください。
- live 環境での自動売買を行う場合は、二重発注対策、ロールバック・監査、モニタリング（Slack 通知等）を必ず整備してください。
- データの整合性確保のため、ETL 実行後は quality.run_all_checks() の結果（QualityIssue）を監視し、重要なエラーが出た際は自動停止またはアラートを上げる運用が推奨されます。

---

この README はコードベースの主要機能と使い方の要約です。詳細は該当モジュール（src/kabusys 以下）のドキュメント文字列（docstring）を参照してください。必要であれば別途インストール手順や実運用ガイド（運用 runbook）を作成します。