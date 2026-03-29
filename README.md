# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータ収集・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ・ETL パイプラインを含む研究・運用向けのコンポーネント群です。モジュール設計によりバックテスト・リサーチ・本番運用（paper/live）それぞれで再利用できます。

主な設計方針
- ルックアヘッドバイアス対策（内部で datetime.today() を直接参照しない等）
- DuckDB を中心としたローカルデータレイヤ
- J-Quants / OpenAI / RSS などの外部 API 呼び出しは明示的に分離・リトライ・フェイルセーフ実装
- ETL や監査ログは冪等（idempotent）に保存

---

## 機能一覧
- データ ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（pagination / rate-limit / retry 対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン run_daily_etl（品質チェック付き）
- データ品質チェック（quality モジュール）
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合などの検出
- ニュース収集（news_collector）
  - RSS 取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存サポート（冪等）
- ニュース NLP（news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア算出（バッチ・JSON mode）
  - スコアのバリデーション・リトライ・スコアクリップ
- 市場レジーム判定（regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース（LLM）を重み付けして日次レジーム（bull/neutral/bear）判定
- ファクター計算 / 研究ツール（research）
  - モメンタム、バリュー、ボラティリティ等のファクター算出
  - 将来リターン計算、IC（Spearman ρ）、統計サマリー、Z-score 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査スキーマ初期化ユーティリティ
  - 監査DB 初期化関数（init_audit_db）
- 環境設定管理（config）
  - .env / .env.local の自動読み込み（パッケージ基準でプロジェクトルートを探索）
  - 必須環境変数のラッパー settings

---

## 要件（主な依存ライブラリ）
- Python 3.9+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリのみで実装されている部分多数）

インストール例（仮想環境推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他開発用依存はプロジェクトの pyproject.toml / requirements.txt を参照
```

---

## セットアップ手順（クイックスタート）
1. リポジトリをクローンしてソースを配置（パッケージは src/kabusys 配下）
2. Python 仮想環境を用意して依存をインストール（上記参照）
3. 環境変数を設定（.env/.env.local または OS 環境変数）
   - 自動で .env/.env.local がプロジェクトルートから読み込まれます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. DuckDB（データベースファイル）用ディレクトリを作成（設定により自動作成する関数もあります）
5. 監査DB を初期化する（必要時）

例: 簡単な .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 設定（環境変数）
重要な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN （必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD （必須）: kabuステーション API のパスワード
- KABU_API_BASE_URL : kabu ステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須）: Slack Bot トークン
- SLACK_CHANNEL_ID （必須）: Slack チャネル ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境（development | paper_trading | live）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意:
- settings を通じて環境変数が必須かどうかが検査されます（未設定でアクセスすると ValueError）。
- 自動 .env 読み込みはプロジェクトルートに .git または pyproject.toml を検出した場合に行われます。

---

## 使い方（サンプル）
以下は典型的なコード実行例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

1) DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュース NLP（OpenAI を使って銘柄別スコアを取得して ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査DB 初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

6) 研究用関数（ファクター計算例）
```python
from kabusys.research import calc_momentum, calc_value
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## ディレクトリ構成（抜粋）
プロジェクトの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（OpenAI 呼び出し・バリデーション）
    - regime_detector.py    — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult エクスポート
    - news_collector.py     — RSS 取得・前処理
    - calendar_management.py— カレンダー管理・営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（z-score）
    - audit.py              — 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - research/ ...その他モジュール

各ファイルはモジュール単位で責務が分離されています。ETL は data.pipeline、AI 評価は ai.*, 研究系は research.* を参照してください。

---

## 注意点 / 運用メモ
- OpenAI と J-Quants の API キーは安全に管理してください。CI に埋め込まないこと。
- 自動 .env ロードはプロジェクトルートの検出に依存します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと安全です。
- DuckDB の executemany はバージョンによって制約があるためコード内で空パラメータの扱い等に注意した実装がされています（pipeline/news_nlp 参照）。
- レート制限やリトライは各クライアントで実装されていますが、運用時は API の最新制約を確認してください。
- 監査テーブルは削除を前提としておらず、監査データは永続化されます。スキーマ初期化は冪等です。

---

## 貢献 / 開発
- バグ修正、テスト追加、ドキュメント改善を歓迎します。プルリクエストの前に issue を立ててください。
- 自動テストや linter（flake8/black 等）設定はプロジェクトルートの設定に従ってください。

---

この README はコードベースに含まれる主要機能・利用方法をまとめた簡易ガイドです。各モジュールの詳細な仕様（引数や返り値の挙動・例外等）はソース内の docstring を参照してください。