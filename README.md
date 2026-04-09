# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買（発注監査含む）を想定したライブラリ群です。  
主に以下を提供します。

- J-Quants API を用いた日次 ETL（株価 / 財務 / 市場カレンダー）の差分取得と DuckDB 保存
- ニュース収集および OpenAI を用いたニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリューなど）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（シグナル → 発注要求 → 約定のトレーサビリティ）
- ニュース RSS 収集（SSRF 対策・トラッキング除去・前処理）

バージョン: 0.1.0

---

## 主な機能一覧（抜粋）

- ETL
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - 差分取得／バックフィル／ページネーション対応
  - J-Quants クライアント（認証トークン自動リフレッシュ、レート制御、リトライ）
- データ品質
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks で一括実行、QualityIssue オブジェクトで報告
- ニュース & AI
  - RSS 取得・記事前処理（news_collector）
  - gpt-4o-mini を用いた銘柄別センチメント score_news（ai_scores テーブルへ保存）
  - 市場レジーム判定 score_regime（ETF 1321 の MA200 とマクロニュースを合成）
- リサーチ
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats にて提供）
- 監査ログ
  - init_audit_schema / init_audit_db により監査用 DuckDB スキーマを初期化
  - signal_events / order_requests / executions のテーブル定義とインデックス
- ユーティリティ
  - 環境設定管理（kabusys.config.Settings）
  - .env 自動ロード（プロジェクトルート基準）および自動ロード無効化フラグ

---

## 動作環境・前提

- Python 3.10+
  - ソース中での型ヒント（X | Y など）を使用しているため 3.10 以上を推奨します。
- 必要な外部ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- J-Quants / OpenAI の API キーが必要（利用する機能に応じて）

推奨: 仮想環境を作成してインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用に以下なども追加
# pip install -e .
```

（プロジェクト配布時は requirements.txt を用意して pip install -r requirements.txt を推奨します）

---

## 環境変数（主要）

kabusys.config.Settings から参照される主要な環境変数とデフォルト値 / 説明:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合に必須）

任意 / デフォルトあり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知の設定
- DUCKDB_PATH: DuckDB データベースのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading のモックフィル方式（instant/partial/never/reject、デフォルト: "instant"）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite のパス（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)、デフォルト INFO

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境作成
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトの requirements.txt がある場合はそれを使用）
4. 環境変数を設定
   - 最低限 JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を設定してください。
   - OPENAI_API_KEY はニュース/レジーム判定を使う場合に必要です。
   - 簡単にはプロジェクトルートに `.env` を作成してください。
5. DuckDB データベースのディレクトリを準備（デフォルト: data/）
   ```bash
   mkdir -p data
   ```
6. 監査 DB を初期化（必要なら）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 基本的な使い方（コード例）

- DuckDB 接続の用意（設定からパス取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 ai_score）を算出して保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

- 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマを接続に適用
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

- RSS を取得して raw_news に保存するフロー（概要）
  - kabusys.data.news_collector.fetch_rss にて記事を取得
  - DB に挿入するためのラッパーを実装して raw_news / news_symbols に保存

（各関数は引数チェック・例外処理を行います。詳細は各モジュールの docstring を参照してください）

---

## 主要モジュールとディレクトリ構成（抜粋）

リポジトリ（src/kabusys）内の主なファイルと簡単な説明:

- src/kabusys/__init__.py
  - パッケージ初期化。__version__ = "0.1.0"
- src/kabusys/config.py
  - 環境変数 / .env 自動読み込み / Settings クラス
- src/kabusys/ai/
  - news_nlp.py : ニュースを集約して OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ保存する
  - regime_detector.py : ETF(ma200) とマクロニュースの LLM スコアを合成して market_regime を書き込む
- src/kabusys/data/
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - jquants_client.py : J-Quants API クライアント（取得・保存関数、リトライ・レート制御）
  - news_collector.py : RSS 取得・前処理・SSRF 対策など
  - calendar_management.py : 市場カレンダーの判定・更新ロジック
  - quality.py : データ品質チェック（QualityIssue）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログ用スキーマ初期化・init_audit_db
  - pipeline.py / etl 関連: ETLResult 等
- src/kabusys/research/
  - factor_research.py : モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリーなど

（実際のファイルツリーはリポジトリの内容に依存します。上記は本 README に含まれる主な実装ファイルの抜粋です。）

---

## 注意点 / 運用上のヒント

- Look-ahead bias を避ける設計が各所に反映されています。多くの関数は target_date を引数に取り、内部で date.today() を使わないようになっています。バッチやバックテストで使用する際は target_date を明示してください。
- OpenAI 呼び出しはネットワーク/レート制御および JSON パース失敗時にフォールバックする設計です。APIキーを環境変数 OPENAI_API_KEY に設定してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。CI やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンの挙動を考慮した保護（params の空チェック等）が各所に入っていますが、使用する duckdb のバージョン差異には注意してください。
- news_collector は RSS 取得時に SSRF 対策（リダイレクト先の検査、プライベート IP 禁止）や受信サイズ制限を行っています。外部 RSS を追加する場合はソースの信頼性とスキーム（http/https）を確認してください。

---

## 開発・貢献

バグ報告や機能改善、ドキュメント修正は Pull Request を歓迎します。テスト・CI の追加、requirements.txt の整備、セットアップスクリプト（pyproject.toml / setup.cfg / poetry 等）の導入を推奨します。

---

README の内容は現状のソースコードに基づいた要約です。各関数・モジュールの詳細な使用法はソース内の docstring を参照してください。必要であれば、特定モジュールの使い方やサンプルコードをさらに追記します。