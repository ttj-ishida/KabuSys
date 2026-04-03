# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究用ファクター算出 → ニュース NLP / LLM を用いたスコアリング → 市場レジーム判定 → 監査ログまでのワークフローをサポートします。

---

## 主要機能（概要）

- データ取得 & ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分更新（バックフィル対応）、ページネーション、レート制御、リトライ処理
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付不整合の検出（QualityIssue オブジェクトで報告）
- ニュース収集・前処理
  - RSS 収集、URL 正規化、トラッキングパラメータ除去、SSRF 対策、冪等保存
- ニュース NLP / LLM スコアリング
  - OpenAI（gpt-4o-mini 等）を使った銘柄別ニュースセンチメント（ai_scores）生成
  - マクロニュースの LLM センチメントと ETF MA を合成した「市場レジーム」判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z-score 正規化
- カレンダー管理
  - JPX カレンダーの差分取得 / 営業日判定 / next/prev trading day 等
- 監査ログ（tracing / audit）
  - signal → order_request → execution といったトレーサビリティ用テーブル群を初期化・提供
- 設定管理
  - .env / .env.local から環境変数を自動読み込み（プロジェクトルート検出）、自動ロード無効化フラグあり

---

## 必要条件

- Python: 3.10+
  - 型ヒントに `X | Y` を使用しているため Python 3.10 以降を想定しています。
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース）

（パッケージ化や requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン（パッケージレイアウト: src/ 配下に kabusys パッケージ）
2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   - 例（pip）
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発モードでローカルインストール（setup/pyproject が整っていれば）
     ```bash
     pip install -e .
     ```
4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` と `.env.local` を配置すると自動読み込みされます。
   - 自動ロードを無効にしたい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD : kabuステーション等のパスワード（必要時）
   - あると便利な設定（省略時はデフォルトを使用）
     - KABUSYS_ENV (development|paper_trading|live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH 等
6. データディレクトリ作成（デフォルトパスを使用する場合）
   ```bash
   mkdir -p data
   ```

例: .env の最小例
```dotenv
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主なユースケース）

以下では Python REPL / スクリプト内での利用例を示します。必要に応じてログ設定等を行ってください。

- DuckDB 接続を作って ETL を実行（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコア算出）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"scored {n_written} codes")
```

- 市場レジーム判定（ETF 1321 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルがある DB にアクセス可能
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 設定オブジェクト
```python
from kabusys.config import settings
print(settings.duckdb_path)           # Path
print(settings.jquants_refresh_token) # 必須（未設定時は ValueError）
```

---

## 注意点 / 実装上の設計ポリシー（要点）

- ルックアヘッドバイアス対策
  - 各モジュールは内部で `datetime.today()` などを直接参照せず、`target_date` を明示的に受け取る設計。
  - DB からのクエリは target_date より前（排他）で取得する等の工夫あり。
- 冪等性とトランザクション
  - ETL / 保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）で実装。
  - audit 初期化などは transactional 引数で BEGIN/COMMIT を選べる。
- API 呼び出しの堅牢性
  - J-Quants / OpenAI 呼び出しにはリトライ、バックオフ、レート制御が組み込まれている。
  - API 失敗時はフェイルセーフ（スコア0.0など）で処理継続する箇所がある。
- セキュリティ対策
  - RSS 取得に SSRF 対策、defusedxml による XML パースの安全化、URL 正規化等を実装。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で使用）
- KABU_API_PASSWORD — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

環境変数が欠けていると Settings プロパティで ValueError が発生する場合があります（必須項目を確認してください）。

---

## ディレクトリ構成（抜粋）

パッケージルート: src/kabusys 以下に主要モジュールがあります。主なファイル:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）処理
    - regime_detector.py     — マクロ + ETF マイナス乖離で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - calendar_management.py — マーケットカレンダー管理 & 営業日ユーティリティ
    - news_collector.py      — RSS 収集・前処理・保存処理
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — z-score 正規化 等の統計ユーティリティ
    - audit.py               — 監査ログ用スキーマ作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — momentum / value / volatility の計算
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai, research, data などがパブリック API を提供

（実際のリポジトリではさらにモジュール・ユーティリティが含まれます）

---

## ロギング / 監視

- 各モジュールは標準 logging を使用しています。必要に応じてハンドラ・レベルを設定してください。
- 実行中プロセス監視用に PID ファイルや kill フラグのパス（Settings.pid_file_path / kill_flag_path）が用意されています。

---

## テスト / 開発時のヒント

- API 呼び出しは各モジュールで差し替え可能な内部関数を使用しているため unittest.mock.patch で依存をモックしやすい設計です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- .env 自動読み込みはプロジェクトルート検出に依存します。テスト時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境設定してください。
- DuckDB は軽量なので開発環境では :memory: を使用してユニットテストを行うことも可能です（例: init_audit_db(":memory:")）。

---

## ライセンス / 貢献

リポジトリ内の LICENSE / CONTRIBUTING ドキュメントに従ってください（この README では特に指定していません）。

---

README に記載の機能はコード内ドキュメント（docstring）に詳細設計や注意点が含まれています。実運用前には必ず設定（特に API キー / トークン）や DB パス、J-Quants の利用制限（レート）を確認してください。