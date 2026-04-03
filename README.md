# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用に設計された Python パッケージです。J-Quants / JPX 等からのデータ取得、ETL、データ品質チェック、ニュース NLP（LLM によるセンチメント）、市場レジーム判定、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション / レート制御 / 再試行）
  - 差分取得・バックフィル対応・冪等保存（DuckDB へ ON CONFLICT DO UPDATE）
  - 日次 ETL エントリーポイント（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付整合性チェック
  - QualityIssue オブジェクトで詳細を収集
- ニュース収集／前処理
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、本文前処理）
  - raw_news / news_symbols と連携する想定（保存ロジックはモジュールに依存）
- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini など）を利用した銘柄ごとのセンチメントスコア化（score_news）
  - マクロニュースを用いた市場レジーム判定（1321 ETF の MA200 と LLM センチメント合成による score_regime）
  - JSON Mode を利用した堅牢なレスポンス検証とリトライ
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Z-score 正規化
- カレンダー管理
  - market_calendar テーブルによる営業日判定（フォールバックロジック含む）
  - カレンダー更新ジョブ（calendar_update_job）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義
  - init_audit_db で監査専用 DuckDB を初期化

---

## 動作要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai (OpenAI SDK v1 系を想定)
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

（実際の requirements.txt / pyproject.toml に基づいてインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトの pyproject.toml / requirements.txt を参照）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（config モジュール内の自動ロード）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN (J-Quants API 用リフレッシュトークン)
   - KABU_API_PASSWORD (kabu ステーション接続用パスワード)
   - OpenAI を利用する機能を使う場合は OPENAI_API_KEY が必要（score_news / score_regime 等）

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（クイックスタート）

以下は Python スクリプトから主要機能を呼ぶ例です。対象は DuckDB を用いたワークフローです。

- 設定値取得
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須
print(settings.duckdb_path)            # デフォルト: data/kabusys.duckdb
```

- DuckDB 接続と日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（LLM）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定（LLM + ETF MA）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って監査テーブルへアクセス可能
```

- market_calendar の問い合わせ例
```python
from kabusys.data.calendar_management import is_trading_day, get_trading_days
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
print(is_trading_day(conn, date(2026, 4, 1)))
print(get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31)))
```

注意点:
- LLM を使う機能（score_news, score_regime）は OpenAI API キーを必要とします（引数 api_key または環境変数 OPENAI_API_KEY）。
- J-Quants 関連処理は JQUANTS_REFRESH_TOKEN を参照して id_token を取得します。
- ETL 実行には J-Quants API のアクセス権が必要です。

---

## 設定の挙動（自動 .env ロード）

- config モジュールはパッケージ内からプロジェクトルートを自動で探索し、`.env` と `.env.local` を読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト等で利用）
- 必須値未設定時は Settings のプロパティが ValueError を投げます（例: jquants_refresh_token、kabu_api_password）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ（src/kabusys 配下）の主要モジュール:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースセンチメント（score_news）
    - regime_detector.py  # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント & DuckDB 保存
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - etl.py              # ETL API 再エクスポート
    - quality.py          # データ品質チェック
    - stats.py            # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py
    - news_collector.py   # RSS 収集・前処理
    - audit.py            # 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

---

## ベストプラクティス・注意事項

- ルックアヘッドバイアス（backtest での未来情報利用）防止のため、多くの関数は内部で date.today() を直接参照しません。対象日を明示的に渡すことを推奨します。
- OpenAI 呼び出しや外部 API はリトライ＆フォールバックロジックを持ちますが、API キー・レート制限・コストに注意してください。
- DuckDB への大量挿入は executemany を使ってまとめて行っていますが、DuckDB のバージョン特性（executemany の空リスト不可など）に注意してください。
- news_collector は SSRF 対策、XML パースの安全化（defusedxml）などを実装しています。外部 RSS を扱う際はソース信頼性に注意してください。

---

## 貢献・拡張

- 新しいデータソース（RSS、API）や戦略ロジック、発注コネクタ（kabu-station 等）を追加できます。
- テストを書く際は、外部 API 呼び出し箇所（OpenAI / J-Quants / HTTP）をモックすることで安定したユニットテストが可能です。config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。

---

README に記載のない内部実装や詳細仕様については、各モジュール（src/kabusys 以下）の docstring コメントを参照してください。必要であれば README にサンプルワークフローや運用手順を追加で作成します。