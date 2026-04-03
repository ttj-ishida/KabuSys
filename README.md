# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチユーティリティ、監査ログ（オーダー／約定トレーサビリティ）といった機能を提供します。

主な設計方針:
- ルックアヘッドバイアスの排除（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を中心としたローカルデータ管理（冪等保存）
- 外部 API 呼び出し（J‑Quants / OpenAI）はリトライ・レート制御・フェイルセーフ実装
- テスト容易性を考慮したトークン注入やモックポイントの用意

---

## 機能一覧（ハイライト）
- データ取得・ETL
  - J‑Quants からの株価日足、財務データ、JPX マーケットカレンダー取得（ページネーション / 冪等保存 / レート制御 / リトライ）
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、XML の安全パース
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを統合して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores へ保存
  - API リトライ・レスポンス検証・スコアクリップ
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを組み合わせた日次レジーム判定（bull/neutral/bear）
- 研究（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリのユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・インデックス作成
  - 監査 DB の初期化用ユーティリティ（DuckDB）

---

## 動作要件
- Python 3.10+
- 必要パッケージ（最低限の例）
  - duckdb
  - openai
  - defusedxml
- （実運用）J‑Quants API と OpenAI の API キーが必要

推奨: 仮想環境を作成してインストールしてください。

---

## 環境変数
パッケージはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（一部）:
- JQUANTS_REFRESH_TOKEN — 必須。J‑Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI 呼び出し時の API キー（関数呼出しで明示的に渡すことも可能）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視関連

.env の書式は標準的な KEY=VALUE に対応し、シングル／ダブルクォートや export プレフィックスを許容します。

---

## セットアップ手順（例）
1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```
2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実際は pyproject.toml / requirements.txt があればそちらを利用してください。
3. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```
4. 環境変数（または .env）を用意
   - 例 `.env`
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡単なコード例）
以下はライブラリをプログラムから利用する最小例です。DuckDB 接続を用意して各 API を呼び出します。

- ETL（日次パイプライン）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

- 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
# conn を使って監査テーブルが作成されていることを確認できます
```

- J‑Quants クライアントを直接利用（デバッグ用）
```python
from kabusys.data import jquants_client as jq
# id_token は get_id_token が settings から自動取得
records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(records))
```

注意:
- OpenAI 呼び出しは api_key を関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J‑Quants は JQUANTS_REFRESH_TOKEN が必要です。settings.jquants_refresh_token を参照します。

---

## 開発時のポイント / 実運用での注意
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。
- ETL / API 呼び出しはリトライやレート制御を備えていますが、API キーやネットワークの制限に注意してください。
- DuckDB に対する複数プロセス同時書き込みなどは注意が必要です（運用設計で排他やキューを検討してください）。
- LLM（OpenAI）呼び出しのレスポンスは厳格にバリデーションされますが、外部依存の失敗時はフェイルセーフ（スコア=0 等）となる設計です。
- Look-ahead バイアスを避けるため、ターゲット日付は明示的に与える使い方を推奨します。

---

## ディレクトリ構成（抜粋）
以下は主要なモジュールと簡単な説明です（リポジトリの src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定の管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM センチメント解析と ai_scores 書き込み
    - regime_detector.py — ETF MA とマクロニュースで市場レジームを判定
  - data/
    - __init__.py
    - pipeline.py        — ETL パイプライン実装（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - jquants_client.py  — J‑Quants API クライアント（fetch/save 関数）
    - news_collector.py  — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py           — zscore 正規化他ユーティリティ
    - quality.py         — 品質チェック群
    - audit.py           — 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリ等

---

## よくある質問 / トラブルシューティング
- .env が読み込まれない:
  - プロジェクトルート検出は __file__ ベースで親ディレクトリを探索します。CWD に依存しません。必要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、自身で os.environ を設定して下さい。
- OpenAI レスポンスが期待どおりでない:
  - レスポンスは JSON のみを期待し、パースできない場合は安全側（スコア=0）になります。調査のため応答内容をログに出す、リトライ回数やタイムアウトを調整するのが有効です。
- DuckDB の挙動:
  - executemany に空リストを渡すとエラーになるバージョン対策の記述がコード中にあります。運用でのバージョンは安定していることを確認してください。

---

この README はコードベースの主要機能と使い方を簡潔にまとめています。より詳細な設計・仕様はソース内ドキュメント文字列（docstring）や関連ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。ご要望があればインストール手順の詳細化、CI／デプロイ手順、サンプルワークフロー（cron / コンテナでの運用）なども追加します。