# KabuSys

日本株向け自動売買／データプラットフォームライブラリ

このリポジトリは「KabuSys」として設計された日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。ETL、データ品質チェック、ニュース収集・NLP、ファクター算出、監査ログ、そして市場レジーム判定など、システム運用に必要なコンポーネント群を提供します。

主な設計方針として「Look‑ahead bias の排除」「データ品質重視」「冪等性」「外部API呼び出しに対する堅牢なリトライ／フォールバック」を採用しています。

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価（OHLCV）・財務・マーケットカレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ対応）
  - 差分更新・バックフィル・ETL 結果集約（ETLResult）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（未来日付や非営業日のデータ）などを検出
- ニュース収集
  - RSS からの安全なニュース収集（SSRF対策・トラッキングパラメータ除去・XML安全パース）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント（ai_scores テーブルへ書き込み）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントを合成）
  - API 呼び出しはリトライやフェイルセーフを備え、レスポンス検証を実施
- リサーチ／ファクター処理
  - Momentum / Volatility / Value 等のファクター算出
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを提供し、シグナルから約定までを UUID でトレース
  - 監査用 DuckDB 初期化ユーティリティを提供
- 環境設定管理
  - .env / .env.local 自動読み込み（OS 環境変数優先）
  - settings オブジェクト経由で全設定を取得

## 必要環境・依存パッケージ

- Python 3.10 以上（types | annotations を使用）
- 主要依存（抜粋）
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージとしてインストールする場合（リポジトリルートで）
pip install -e .
```

（プロジェクトに setup/pyproject があればそちらを利用してください。）

## 必要な環境変数

主に以下を使用します。`.env` または `.env.local` に設定するか OS 環境変数で与えてください。自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基に行われます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL / jquants_client）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文連携を行う場合）

任意/機能依存:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector の API 呼び出し）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

設定が不足している場合、Settings プロパティで ValueError が発生します（必須設定は明示的に require されます）。

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
2. 依存パッケージをインストール（上記参照）
3. プロジェクトルートに .env を作成（例: JQUANTS_REFRESH_TOKEN=xxx）
4. データベースディレクトリの作成（必要に応じて）
   - デフォルトで data/ 配下に duckdb ファイルを作成します

## 使い方（コード例）

以下は主要なユースケースの最小例です。詳細は各モジュールの docstring を参照してください。

- ETL（日次）を実行する:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI API キー必須）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら環境変数を使用
print("書き込み件数:", n_written)
```

- 市場レジームスコアを算出（ma200 + マクロニュース）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # 別 DB を指定することも可能
```

- 環境変数自動ロードの無効化（テスト時など）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('auto load disabled')"
```

## 実装上の注意点 / 設計メモ

- Look‑ahead bias を避けるため、日付計算は target_date を明示的に受け取り、内部で date.today() を参照しない設計の関数が多くあります（研究・NLP・レジーム判定など）。
- OpenAI 呼び出しは JSON Mode を想定し、レスポンスの厳密なバリデーションとリトライ（指数バックオフ）を行います。API エラー時はフェイルセーフ（スコア 0.0 など）で続行します。
- J-Quants クライアントはレート制御（120 req/min）、401 時のトークン自動リフレッシュ、ページネーション処理を備えています。
- DuckDB への保存はできるだけ冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行います。
- ニュース収集は SSRF 対策、XML の安全パーシング、トラッキングパラメータ除去、受信サイズ制限を実装しています。

## ディレクトリ構成

（リポジトリ内の主要なファイル／モジュール）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄別スコア）
    - regime_detector.py           — 市場レジーム判定（ma200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                       — ETL インターフェース再エクスポート
    - news_collector.py            — RSS ニュース収集・前処理
    - calendar_management.py       — マーケットカレンダー管理（営業日判定等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（schema / init）
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等

（上記以外に strategy / execution / monitoring 等のパッケージが想定されていますが、今回のコードベースでは主に data / ai / research / config が実装されています）

## トラブルシューティング

- OpenAI / J-Quants の API キーが未設定だと ValueError が発生します。関数の docstring を参照して api_key 引数または環境変数を設定してください。
- DuckDB のファイルパス権限やディレクトリ未作成でエラーが出る場合は、親ディレクトリを作成してください（init_audit_db は自動で親ディレクトリを作成します）。
- テスト環境で .env 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

詳細な API（関数引数や戻り値、エラー条件）は各モジュールの docstring に記載しています。まずは上記の簡易手順で環境を整え、ETL → 品質チェック → ニューススコア → レジーム判定の流れを順に触ってみてください。必要であれば README を拡張して CLI ツールやサンプルジョブスクリプトの使い方を追加します。