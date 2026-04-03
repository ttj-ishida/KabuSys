# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

本ドキュメントは提供されたコードベースに基づく簡易ドキュメントです。実行前に各種設定（APIキー・DBパス等）を適切に用意してください。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの自然言語処理によるセンチメント評価、そして市場レジーム判定などを行うためのモジュール群を提供します。DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini 等）をニュース解析に利用します。ETL、品質チェック、監査ログ（監査テーブル初期化）などデータ基盤と研究／戦略層のためのユーティリティが含まれます。

設計方針として、バックテストやモデル評価でのルックアヘッドバイアスを避ける工夫（日時の明示的な引数化や過去のみ参照）や、APIの堅牢化（リトライ、レート制御、フォールバック）が盛り込まれています。

主な利用ケース:
- J-Quants から株価・財務・カレンダーを差分 ETL で取得・保存
- RSS からニュース収集 → OpenAI で銘柄別センチメントを算出して保存
- ニュースと価格の情報を組み合わせた市場レジーム判定
- 研究用ファクター計算・IC/統計解析
- 監査ログテーブルの初期化（発注/約定トレース用）

---

## 機能一覧

大分類と主要機能（ファイル／モジュール名）

- 設定管理
  - `kabusys.config` : .env 自動読み込み（.env.local を優先）、環境変数ラッパー（settings）
- AI / ニュース解析
  - `kabusys.ai.news_nlp.score_news` : raw_news → OpenAI で銘柄別 ai_score を ai_scores に書き込む
  - `kabusys.ai.regime_detector.score_regime` : ETF(1321) の MA200 とマクロニュースで市場レジーム判定
- Data（ETL / 品質 / カレンダー / J-Quants クライアント）
  - `kabusys.data.pipeline` : 日次 ETL（run_daily_etl 等）
  - `kabusys.data.jquants_client` : J-Quants API 呼び出し & DuckDB 保存ユーティリティ（fetch / save）
  - `kabusys.data.news_collector` : RSS 取得・前処理・raw_news 保存
  - `kabusys.data.quality` : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - `kabusys.data.calendar_management` : 市場カレンダーの判定・更新ロジック
  - `kabusys.data.audit` : 監査テーブルの初期化（init_audit_schema / init_audit_db）
  - `kabusys.data.stats` : z-score 正規化など統計ユーティリティ
- Research（ファクター計算 / 特徴量解析）
  - `kabusys.research.factor_research` : momentum / value / volatility 等のファクター
  - `kabusys.research.feature_exploration` : 将来リターン / IC / 統計サマリ等

セーフティ・運用面:
- API のレート制御・リトライ・トークン自動リフレッシュ（jquants_client）
- ニュース収集の SSRF 対策、XML attack 対策（defusedxml）
- .env 自動ロード（プロジェクトルート検出）でテスト時は無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## セットアップ手順

前提
- Python 3.10 以上（"X | Y" 型注釈を使用しているため）
- DuckDB を利用（Python パッケージ）
- OpenAI Python SDK（news_nlp/regime_detector で使用）
- defusedxml（RSS パース保護）

例: pip でのインストール（仮想環境推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順位: OS env > .env.local > .env）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須、ETL 実行時）
- OPENAI_API_KEY : OpenAI API キー（news scoring / regime 判定 実行時）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（発注モジュールがある場合）
- DUCKDB_PATH : DuckDB ファイルパス（例: data/kabusys.duckdb）デフォルトあり
- SQLITE_PATH : 監視用 sqlite パス（オプション）
- KABUSYS_ENV : development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例: .env (最小)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な関数呼び出し例）

下のコード例は Python REPL / スクリプトでの利用例です。`duckdb` の接続引数は実運用に合わせて変更してください。

1) DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

2) ニュースセンチメントを算出して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key は None の場合環境変数 OPENAI_API_KEY を参照
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（ETF 1321 の ma200 とマクロニュース合成）
```python
from kabusys.ai.regime_detector import score_regime
# conn は duckdb 接続、api_key は OPENAI_API_KEY または引数
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用の DuckDB を初期化（監査スキーマ作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# init_audit_db は transactional=True でスキーマ作成します
```

5) ETL 結果の確認（ETLResult）
- run_daily_etl の戻り値は ETLResult 型。`to_dict()` で JSON 互換の辞書として取得可能です。

注意事項・運用メモ
- OpenAI 呼び出しはリトライロジックを持ちますが、APIキーやレート制限の状況に注意してください。
- news_nlp と regime_detector はテスト容易性のため API 呼び出し部分を差し替え可能（モックパッチ）。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン考慮あり（モジュール内で対策済み）。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（提供されたスナップショットに基づく）。実際のリポジトリはさらにファイルが存在する可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - audit.py
      - calendar_management.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - quality.py
      - stats.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - その他: strategy, execution, monitoring（パッケージ __all__ に含まれるがコードスニペット未提示）

主要モジュールと役割:
- kabusys/config.py: 環境変数読み込み、settings オブジェクト
- kabusys/ai: ニュース NLP とレジーム判定
- kabusys/data: ETL / J-Quants クライアント / 品質チェック / ニュース収集 / 監査ログ
- kabusys/research: ファクター計算と解析ツール

---

## 環境変数・設定の詳細

- 自動 .env ロード
  - 起点は本モジュールのファイルパスから親ディレクトリを上へ探索し、`.git` または `pyproject.toml` を見つけたディレクトリをプロジェクトルートと見なします。そこにある `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- Settings（kabusys.config.settings）
  - jquants_refresh_token → JQUANTS_REFRESH_TOKEN（必須）
  - kabu_api_password → KABU_API_PASSWORD（必須）
  - kabu_api_base_url → KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
  - line_channel_access_token, line_user_id → LINE 関連（通知用）
  - duckdb_path, sqlite_path → データベースパス
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start → 監視・プロセス管理
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct → 監視閾値
  - KABUSYS_ENV → development | paper_trading | live（不正値はエラー）
  - LOG_LEVEL → 文字列（DEBUG など）

---

## 開発・テスト上の注意

- API 呼び出し部（OpenAI、J-Quants、HTTP）のテストはモック化可能（各モジュール内で呼び出し関数を patch する設計）。
- ニュース収集は外部ネットワーク・RSS の挙動に依存するため、ユニットテストでは fetch_rss / _urlopen をモックしてください。
- DuckDB に対する操作（DDL / INSERT）を含む関数はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されている箇所がありますが、初期化系は transactional フラグを利用して安全に実行してください。

---

## ライセンス・貢献

（このリポジトリのライセンス情報はここに追記してください。コントリビュート手順やコードスタイルはプロジェクトに合わせて整備してください。）

---

README はここまでです。必要があれば、セットアップ向けの docker-compose サンプル、CI ワークフロー、より詳細な .env.example、あるいは各モジュールの API リファレンス（関数シグネチャと引数説明）を追加できます。どの情報を優先して追加しますか？