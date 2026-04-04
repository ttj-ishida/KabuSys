# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの差分取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定トレース）など、研究／運用に必要な機能をモジュール単位で提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複検出、日付整合性検査（run_all_checks）
- ニュース収集・NLP（AI）
  - RSS 取得・前処理・raw_news への保存（news_collector.fetch_rss）
  - OpenAI（gpt-4o-mini）でニュースを銘柄毎にスコアリングし ai_scores に書き込む（score_news）
  - マクロニュース + ETF（1321）の MA200 乖離を合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフ・フォールバック設計
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー（calc_forward_returns / calc_ic / factor_summary）
  - Zスコア正規化ユーティリティ（zscore_normalize）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブルを DuckDB に初期化（init_audit_schema / init_audit_db）
  - 発注フローの UUID 連鎖とステータス管理を前提設計
- 運用サポート
  - 環境変数管理（.env 自動読み込み、.env.local 優先）
  - PID / kill flag /リソース閾値などの監視設定

設計哲学の一部:
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない設計）
- 冪等性を重視（DB 書き込みは上書き可・重複回避）
- テストしやすさ（OpenAI 呼び出しの差し替え等を想定）

---

## 要求環境

- Python 3.10 以上（型ヒントの `X | None` 表記を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他：標準ライブラリ（urllib, json, logging 等）

インストール例（仮の requirements がない場合）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

このリポジトリがパッケージ化されている場合は:
```bash
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（説明）:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（必須：ETL・jquants_client が使用）
- OPENAI_API_KEY
  - OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD
  - kabuステーション API 用パスワード（発注系で使用）
- KABU_API_BASE_URL
  - kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - LINE 通知用（任意）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - 実行監視用ファイルパス・設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視閾値（%）
- KABUSYS_ENV
  - 実行環境: development / paper_trading / live
- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意:
- settings.jquants_refresh_token は必須です（設定されていない場合 ValueError が発生します）。
- .env の書式は Bash ライクな形式に対応（export PREFIX=...、クォート、コメント等）。

---

## セットアップ手順（簡易）

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install -e .            # パッケージ化されていれば編集可能インストール
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数を準備
   - プロジェクトルートに `.env`（および `.env.local`）を作成するか、環境変数を export してください。
   - 最低限必要な変数例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース初期化（監査用 DB など）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb.DuckDBPyConnection
     ```

---

## 使い方（主要 API の例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の作成（settings からパスを利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日を使用
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコアを生成する「営業日」。（ニュースウィンドウは前日15:00 JST ～ 当日08:30 JST）
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {written} symbols")
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

---

## 自動読み込みされる .env の仕様・注意

- 自動ロードはプロジェクトルートを `.git` または `pyproject.toml` を手掛かりに探索します（__file__ ベース）。そのため CWD に依存しません。
- 読み込み順序:
  1. OS 環境変数（既に設定されている場合は保護される）
  2. .env（プロジェクトルート）
  3. .env.local（上書き）
- 無効化:
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースは Bash ライクな形式に対応し、コメントや export プレフィックス、クォート、インラインコメント等に対応しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM ベーススコアリング
    - regime_detector.py    — ETF + マクロで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 取得・前処理
    - calendar_management.py— 市場カレンダー管理（営業日判定等）
    - quality.py            — データ品質チェック
    - stats.py              — Zスコア等統計ユーティリティ
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py— 将来リターン / IC / 統計サマリー

（上記は主要モジュールの抜粋です）

---

## テスト・モックについて

- OpenAI 呼び出しなど外部 API は内部の _call_openai_api を unittest.mock.patch で差し替え可能です（news_nlp._call_openai_api / regime_detector._call_openai_api をモックしてレスポンス検証を行えます）。
- jquants_client の HTTP レイヤーも単体でテスト可能です（ネットワークエラーや 401 のリフレッシュ挙動を模擬）。

---

## トラブルシューティング（よくある問題）

- ValueError: "環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません。"
  - .env または環境に JQUANTS_REFRESH_TOKEN を設定してください。
- OpenAI 関連のタイムアウト・エラー
  - ネットワークやレート制限によりリトライされます。API キーやネットワーク設定、モデル名の互換性を確認してください。
- DuckDB 保存での executemany の空リストエラー
  - 一部関数は DuckDB のバージョン制約を避けるため空リストを渡さない実装を行っています。呼び出し側のデータ有無を確認してください。

---

## 最後に / 設計メモ

このコードベースは「研究（リサーチ）フェーズ」と「運用（実資金/模擬）」フェーズ双方を想定しており、以下の点を重視しています。

- look-ahead bias の排除（バックテスト用に同じ関数を使えるように設計）
- 冪等性（ETL・保存処理）
- 障害耐性（外部 API のリトライ / フェイルセーフ）
- 監査可能性（監査テーブルによるトレーサビリティ）

README の内容やサンプルで不足している操作（たとえば kabu ステーションとの接続や発注フローの実装）は、プロジェクトの運用方針に応じて別途追加してください。

---

必要であれば、README に含めるサンプル .env.example、さらに詳しいデプロイ手順（systemd / Docker / CI/CD 用の構成）や具体的な CLI スクリプト例も作成します。どの情報を追加したいか教えてください。