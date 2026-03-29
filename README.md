# KabuSys

日本株向けのデータ基盤・自動売買補助ライブラリ群です。ETL（J-Quants からのデータ取得→DuckDB 保存）、ニュースの自然言語処理による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを含みます。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を中心とした軽量な永続化」「外部 API 呼び出しはリトライ・フェイルセーフ化」「ETL／品質チェックの冪等性と部分失敗許容」です。

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（duckdb）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合検出（quality モジュール）
- ニュース収集・処理
  - RSS フィード取得（SSRF 対策・サイズ制限・URL正規化）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI を利用）
  - 銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）
  - JSON mode / リトライ・エラーハンドリングを備える
- 研究用ユーティリティ
  - ファクター算出（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - init_audit_db で監査用 DuckDB を作成
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、Settings オブジェクト（環境変数ラッパー）
  - 自動読み込みを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 動作要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース など）

実際のプロジェクトでの pip 要件ファイルは本リポジトリに含まれていないため、上記を適宜インストールして下さい。

例:
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# またはパッケージ配布があれば: pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存ライブラリをインストール（上記参照）
3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（get_id_token 用）
   - OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD      — kabuステーション API パスワード（注文モジュール等で使用）
   - SLACK_BOT_TOKEN        — Slack 通知用 bot token
   - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
   - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — SQLite 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV            — 環境: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL              — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

※ 実行例は Python REPL / スクリプト内での利用を想定しています。詳細は各関数の docstring を参照してください。

- 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続を開いて ETL を実行（日次 ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定（ETF 1321 をベースに ma200 とマクロニュースを組み合わせる）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーン設定が適用されます
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
```

---

## 自動 .env 読み込みの挙動

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、以下の順で環境変数を読み込みます:
  1. OS 環境変数（優先）
  2. .env.local（override=True、OS 環境変数は保護）
  3. .env（override=False：未設定キーのみセット）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風に `export KEY=val` やクォート、インラインコメントなどに対応しています。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py                  — パッケージ初期化（バージョン等）
    - config.py                     — 環境変数 / Settings 管理・自動ロード
    - ai/
      - __init__.py                 — ai API エクスポート
      - news_nlp.py                 — ニュースのセンチメントスコアリング（OpenAI）
      - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py           — J-Quants API クライアント＆DuckDB 保存関数
      - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
      - etl.py                      — ETLResult 再エクスポート
      - stats.py                    — 統計ユーティリティ（zscore_normalize）
      - quality.py                  — データ品質チェック（欠損・重複・スパイク等）
      - news_collector.py           — RSS 取得・前処理・保存（SSRF 対策等）
      - calendar_management.py      — 市場カレンダー管理・営業日判定
      - audit.py                    — 監査テーブル定義・初期化
    - research/
      - __init__.py
      - factor_research.py          — モメンタム/バリュー/ボラティリティ等の計算
      - feature_exploration.py      — 将来リターン/IC/統計サマリー 等
    - ai, research, data 以下に細かいユーティリティや DB 操作ロジックが入っています。

---

## ロギング・環境

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- ETL / API 呼び出し系は info/warn/error ログを多用しています。運用時はファイルローテーションや外部ロギング（CloudWatch 等）を検討してください。

---

## 注意事項 / 運用メモ

- OpenAI / J-Quants API のキーは厳重に管理してください。ローカルでのテストは最小限のデータ量で行い、API コストに注意してください。
- DuckDB をバックエンドに使っていますが、バックアップ戦略（定期コピー）やファイルロックの運用には注意してください（複数プロセスが同一ファイルを同時に更新する設計には注意が必要です）。
- ニュース収集や OpenAI 呼び出しは外部APIに依存するため、ネットワークエラーやレート制限に備えた監視が必要です。モジュール内部でリトライやフォールバック（ゼロスコア等）を行いますが、長期的な失敗は運用アラートに繋げてください。
- 本ライブラリは取引・注文実行機能を含む設計を意図していますが、実際に売買を行う前にオフラインで十分に検証して下さい（特に live 環境での動作確認）。

---

必要であれば、README にテスト実行方法や CI 設定、より詳細な API リファレンス（各関数のパラメータ説明）を追加します。どの項目を拡張するか教えてください。