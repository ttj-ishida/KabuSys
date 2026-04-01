# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のコアライブラリ（モジュール群）。  
ETL、ニュース収集・NLP、ファクター算出、研究用ユーティリティ、監査ログ、J-Quants / kabuAPI クライアント等を含みます。

主な目的は「データ収集→品質チェック→ファクター算出→シグナル/発注の監査可能な流れ」を提供することです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（短いコード例）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- 説明: 日本株の自動売買システム向けの基盤ライブラリ群。データETL（J-Quants）、ニュース収集・NLP（OpenAI 利用）、ファクター/リサーチユーティリティ、監査ログ（DuckDB）、マーケットカレンダー管理など、運用に必要なコンポーネントを揃えています。
- 主要言語: Python
- 状態: コードベース（README はこのソースに基づく利用説明）

---

機能一覧
- 設定管理
  - 環境変数/.env の自動読み込み（.env, .env.local、無効化フラグあり）
  - settings オブジェクトを通した設定アクセス（J-Quants, kabuAPI, Slack, DB パス等）
- データ（data）
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - ETL パイプライン（差分取得・バックフィル・品質チェックの統合 run_daily_etl）
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS、安全対策、前処理、raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ生成・初期化（signal_events, order_requests, executions）
  - DuckDB への冪等保存関数
- AI（ai）
  - ニュースセンチメント（gpt-4o-mini を利用する JSON 出力モード）
    - news_nlp.score_news: 銘柄ごとの ai_score を ai_scores テーブルへ書込
  - 市場レジーム判定
    - regime_detector.score_regime: ETF（1321）MA とマクロニュースを合成して market_regime に保存
  - リトライ / フェイルセーフ設計（API失敗時は安全側へフォールバック）
- Research（research）
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats）
- 実行/監視（monitoring 等）
  - （コードベースに監視設定用のパラメータがあるため運用監視に統合可能）

---

セットアップ手順（ローカル開発向け）
1. Python の準備
   - 推奨: Python 3.10+（コード内の型ヒントや union 演算子等に依存）
2. 仮想環境を作る
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. 必要ライブラリをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
4. パッケージを編集可能インストール（オプション）
   - pip install -e .
     - （セットアップ用ファイルがある場合）
5. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.git または pyproject.toml を基準に探索）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
6. DB の初期化（監査ログ用）
   - Python から DuckDB 接続を作り、監査スキーマを初期化できます（例は後述）。

注意:
- 自動読み込みはプロジェクトルートを検出できない場合はスキップされます。
- 実運用では OpenAI / J-Quants の API キーや各種パスは安全に管理してください（CI/CD シークレット等）。

---

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token 用）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- 省略可（デフォルトあり）
  - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite path（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env)
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

使い方（コード例）

- 共通: settings の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI スコア）を実行
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
print(f"scored {count} codes")
```

- 市場レジームスコア保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# duckdb 接続は上記と同様に作成
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査テーブルが作成された DuckDB 接続
```

注意点:
- OpenAI 呼び出しは外部 API で課金が発生します。api_key を与えるか環境変数 OPENAI_API_KEY を設定してください。
- ETL / AI モジュールはいずれもルックアヘッドバイアスを避ける設計（内部で date.today() を不用意に使わない）になっています。バックテストや再現性を担保するには target_date を明示的に指定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NPL（スコア生成）
    - regime_detector.py             — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl など）
    - etl.py                         — ETL インターフェース再エクスポート
    - calendar_management.py         — マーケットカレンダー管理（営業日判定など）
    - news_collector.py              — RSS ニュース収集（SSRF/サイズ対策あり）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                       — 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等の計算
    - feature_exploration.py         — forward returns / IC / 統計サマリー 等
  - (その他: strategy, execution, monitoring モジュールが __all__ に含まれる想定)

この README はリポジトリ内のソースからの抜粋・要約です。個々の関数やモジュールには詳細な docstring が付いているため、利用時は該当モジュールの docstring を参照してください。

---

運用上の注意・設計方針（補足）
- API 呼び出し（OpenAI / J-Quants）にはリトライとバックオフが実装されていますが、運用時はレート制限やコストに注意してください。
- ニュース収集では SSRF 対策や最大受信サイズチェック、トラッキングパラメータ削除等の安全措置があります。
- データ品質チェックは Fail-Fast ではなく検出結果を集めて返す設計です。ETL の自動停止/警告の扱いは呼び出し側で決めてください。
- 監査ログは削除しない前提で設計されています（トレーサビリティ重視）。

---

問題報告 / 開発
- バグや改善要望はリポジトリの issue に記載してください。
- 開発時は仮想環境を利用し、依存関係は requirements.txt / pyproject.toml を整備の上で管理してください。

---

以上です。README の補足や特定機能の使い方（例: ETL のカスタム引数、OpenAI のレスポンス検証挙動、DuckDB スキーマ詳細など）が必要でしたら、どの項目を拡張するか教えてください。