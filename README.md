# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants からの市場データ取得・ETL、ニュース収集と LLM によるニュースセンチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を盲目的に使わない）
- DuckDB を中心としたローカル DB ベースの ETL と品質チェック
- J-Quants / OpenAI API 呼び出しに対する堅牢なリトライ・レート制御
- 冪等性（idempotency）を重視した保存処理

---

## 機能一覧

- データ基盤（data）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（トークン管理、ページング、レート制御、保存用ユーティリティ）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS -> raw_news、SSRF 対策・トラッキングパラメータ除去）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）

- AI（ai）
  - ニュースのセンチメント付与（news_nlp.score_news） — OpenAI（gpt-4o-mini）を利用
  - マクロ要因と移動平均乖離を使った市場レジーム判定（regime_detector.score_regime）

- 研究（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 共通ユーティリティ
  - 環境変数管理（kabusys.config）
  - 統計ユーティリティ（zscore_normalize など）

---

## 必要条件（依存）

主な Python パッケージ（ソース内参照）
- duckdb
- openai
- defusedxml

その他標準ライブラリを多用しています（urllib, json, datetime, logging など）。

環境に応じて適切な Python バージョン（3.10+ 推奨）を用意してください。

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトディレクトリへ移動）

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   (プロジェクトに requirements.txt がある場合はそれを用いる。例:)
   ```bash
   pip install duckdb openai defusedxml
   # または
   pip install -e .
   ```

4. 環境変数の設定
   - .env（プロジェクトルート）に必要な値を設定します。自動で .env を読み込む機能があり、優先度は OS 環境変数 > .env.local > .env です。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 BOT トークン
   - SLACK_CHANNEL_ID      : 通知先チャンネル ID

   任意（デフォルトあり）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABUS_API_BASE_URL    : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite path（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 呼び出しで使用）

5. DB 初期化（監査ログ用等）
   - 監査ログ専用 DB を作成してスキーマを初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続へ監査スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要 API と実行例）

以下は基本的な呼び出し例です。各関数は DuckDB 接続（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続作成例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー + 株価 + 財務 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントスコア付与（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数か引数で指定
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {count}")
  ```

- 市場レジーム判定（MA200 + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 統計・正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

メモ:
- OpenAI 呼び出しは失敗時にフェイルセーフ（0 相当でフォールバック）を行う箇所が多く、API_KEY 未設定時は例外になる場合があります。テストやローカルではモックして呼び出すことが可能です（各モジュールの _call_openai_api を patch）。

---

## 環境変数の自動読み込み挙動

- パッケージ内の `kabusys.config` はプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位:
  1. OS 環境変数
  2. .env.local
  3. .env
- 自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — マーケットレジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — 市場カレンダー管理
    - news_collector.py           — RSS ニュース収集（SSRF 対策）
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化 / init_audit_db
    - etl.py                      — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py          — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在を仮定するモジュール群：README に明示)
  - strategy/ (戦略実装層)
  - execution/ (発注・約定ハンドリング)

（実際のファイルはプロジェクト内の src/kabusys 以下を参照してください）

---

## ロギング / エラーハンドリング

- モジュール内で logging を利用しており、LOG_LEVEL 環境変数で出力レベルを調整できます（デフォルト INFO）。
- API 呼び出し（OpenAI、J-Quants、RSS 取得）にはリトライ・バックオフ・フォールバックや保護措置（SSRF 検査、受信サイズ制限など）が組み込まれています。
- ETL は部分失敗に強く、各ステップで例外をキャッチして処理を継続する設計です。ETLResult にエラー情報や品質チェックの結果が蓄積されます。

---

## テスト / モック化について

- OpenAI API 呼び出しや外部 HTTP は各モジュール内部の `_call_openai_api` / `_urlopen` 等をモックすることで単体テストが可能です。
- DuckDB 接続をインメモリ（":memory:"）で与えれば、DB 周りのテストが容易です。

---

## ライセンス / 貢献

- この README はコードベースを元に自動生成しています。実際のライセンスや貢献フローはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---

README でカバーしてほしい追加点（例：実行スクリプト、CI 設定、より詳しい環境変数の例）があれば教えてください。README を追記・調整します。