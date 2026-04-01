# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、アルゴリズムトレーディング基盤に必要な機能をモジュール化しています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（.env / .env.local の自動読み込み）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得／保存（DuckDB）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 日次差分取得（calendar / prices / financials）と品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで取得
- ニュース収集（RSS）モジュール
  - URL 正規化、SSRF 対策、受信サイズ制限、重複防止（ハッシュID）
  - raw_news / news_symbols / ai_scores への保存設計を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）でセンチメント分析し ai_scores に書き込み（バッチ／リトライ）
  - タイムウィンドウは前日15:00 JST～当日08:30 JST（UTC に変換して処理）
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日MA乖離（70%）とマクロニュース LLMセンチメント（30%）を合成して 'bull'/'neutral'/'bear' を判定
  - API失敗時はフェイルセーフでマクロ貢献を 0.0 にフォールバック
- リサーチ（ファクター計算・特徴量解析）
  - モメンタム、バリュー、ボラティリティ等の計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー、Zスコア正規化ユーティリティ
- データ品質チェックモジュール（quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ（DuckDB）
  - 監査トレースのための DDL・インデックス整備

---

## セットアップ手順

前提：
- Python 3.9 以上（typing の | 型注釈と一部モダン機能を想定）
- DuckDB を利用（ローカルファイル or :memory:）

1. リポジトリをチェックアウト（ソースが src/kabusys 構成）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - ※ 実運用で Slack 連携等を使う場合は別途 slack_sdk 等を追加
4. パッケージをインストール（開発時は editable 推奨）
   - pip install -e .

環境変数 / .env:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）で `.env` および `.env.local` を使用できます。
- 自動読み込みはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも各機能を使う際に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL / jquants_client）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- OPENAI_API_KEY — OpenAI を使うモジュール（news_nlp, regime_detector）で必要（関数引数で渡すことも可能）

その他オプション:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 .env（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な利用例）

以下は Python スクリプト／ REPL での代表的な呼び出し方です。DuckDB 接続には settings.duckdb_path を使用できます。

1) DuckDB 接続例
- from kabusys.config import settings
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

2) ETL（日次パイプライン）を実行
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日を基準に処理
- print(result.to_dict())

3) ニューススコア（OpenAI）を実行
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026, 3, 20))
- print(f"scored {count} codes")

- ※ OpenAI API キーを明示的に渡す場合:
  - score_news(conn, date(2026,3,20), api_key="sk-...")

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20))

5) ファクター計算・リサーチユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- mom = calc_momentum(conn, target_date=date(2026,3,20))
- val = calc_value(conn, target_date=date(2026,3,20))

6) 監査ログスキーマ初期化（監査用 DB を作る）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")
- # 既存 conn にスキーマを追加する:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

7) データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

注意点:
- AI (OpenAI) を使う関数は、デフォルトで環境変数 `OPENAI_API_KEY` を参照します。引数で api_key を渡すこともできます（テスト時の差し替えに便利）。
- ETL / データ保存は DuckDB のテーブルを前提としています。初期スキーマの作成は別途 schema 初期化関数がある想定（本コードベースの外にあることが多い）。

---

## 自動環境読み込みの動作

- .env / .env.local がプロジェクトルート（.git または pyproject.toml を基準）にある場合、起動時に自動で読み込まれます。
- 読み込み順序:
  - OS 環境変数（既存） を優先
  - .env を読み込み（未設定キーのみ）
  - .env.local を読み込み（上書き可能、ただし OS 環境変数は保護）
- 自動ロードを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env のパース仕様:
- export KEY=val の形式を許可
- シングル/ダブルクォートをサポート（エスケープ処理あり）
- コメントの扱いなどは .env の一般的挙動に合わせています（LINE レベルで解釈）

---

## ディレクトリ構成

（主なファイル／モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                                — 環境変数／設定管理
  - ai/
    - __init__.py
    - news_nlp.py                             — ニュース NLP（OpenAI）と ai_scores 書込
    - regime_detector.py                      — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                       — J-Quants API クライアント（fetch/save）
    - pipeline.py                             — ETL パイプライン（run_daily_etl 等）
    - etl.py                                  — ETL インターフェース再エクスポート（ETLResult）
    - stats.py                                — zscore_normalize 等の統計ユーティリティ
    - quality.py                              — データ品質チェック
    - calendar_management.py                  — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py                       — RSS ニュース収集（SSRF 対策等）
    - audit.py                                — 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py                      — モメンタム／バリュー／ボラティリティ等
    - feature_exploration.py                   — 将来リターン、IC、summary, rank
  - ai, data, research の他、strategy / execution / monitoring 等のトップレベルパッケージ名は __all__ に宣言されています（将来的な拡張向け）。

---

## 開発・運用メモ・トラブルシューティング

- OpenAI 呼び出しはリトライとフェイルセーフ（失敗時はゼロスコア）を備えていますが、APIキー・レート制限（料金）には注意してください。
- J-Quants API は 120 req/min 相当の制限を守るため内部で RateLimiter を使用しています。大量一括処理ではスロットリングを考慮してください。
- DuckDB の executemany は空リストを渡すと問題になるバージョンがあるため、実装は空チェックを行っています。
- ETL 実行時は先に market_calendar を更新して営業日判定に使う設計になっています（カレンダーがない場合は曜日ベースのフォールバックを行う）。
- テスト時は各種外部呼び出し部分（OpenAI クライアント、ネットワークアクセス等）をモックしやすいように設計されています（関数を patch できる構造）。

---

## ライセンス / 貢献

このREADME はコードベースに基づいた説明書です。実運用の前に必ずテストとセキュリティチェック（APIキー管理、ネットワークアクセス制限等）を行ってください。  
貢献や改善提案はプルリクエスト／Issue を通じて歓迎します。

---

必要であれば、README に実際の SQL スキーマ初期化手順、より詳細な .env.example、実行用スクリプト例（systemd / cron / Airflow のサンプル）なども追加します。どの付録が要りますか？