# KabuSys

日本株向けの自動売買システム用ライブラリ（パッケージ）です。データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査/スキーマ管理など、戦略開発と運用に必要な基盤機能を提供します。

---

## 主な概要

- DuckDB をデータレイヤとして用い、J-Quants API や RSS などからデータを取得して保存・加工します。
- 研究（research）→ 特徴量（features）→ 戦略（strategy）→ 発注（execution）という層構造を想定した設計です。
- ルックアヘッドバイアス対策、冪等性（idempotent 操作）、API レート制御、SSRF 対策等の実務的考慮が組み込まれています。

パッケージ名: kabusys  
バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 機能一覧

- 環境設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（settings オブジェクト）
- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（株価・財務・マーケットカレンダー取得）
    - レートリミット、リトライ、トークン自動リフレッシュ対応
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days 等）
  - RSS ベースのニュース収集（SSRF対策・サイズ制限・トラッキング除去）
  - DuckDB スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution の多層スキーマ
- 研究 / ファクター（kabusys.research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、要約統計
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターをマージ・フィルタ・Zスコア正規化し `features` テーブルへ保存
- シグナル生成（kabusys.strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算
  - BUY/SELL シグナル生成（Bear レジーム抑制、ストップロス等のエグジット判定）
  - signals テーブルへ日付単位で置換（冪等）
- 監査・発注基盤（schema / audit）
  - signal_events, order_requests, executions 等の監査テーブル定義
- 汎用ユーティリティ
  - zscore_normalize（クロスセクション正規化）など

---

## 必要要件

- Python 3.10 以上（PEP 604 の型記法（A | B）を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（実際の requirements.txt はプロジェクト側で管理してください。最低限 duckdb と defusedxml はインストールしてください。）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# あるいはプロジェクトの requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン（既にパッケージ配布されている場合はインストール）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```

2. 必須環境変数を設定
   - プロジェクトルートに `.env` を置くか、OS 環境変数で設定します。
   - 参考となるファイル（.env.example）を用意している場合はそれをコピーして編集してください。

   必須の環境変数（コード内で _require() によりチェックされます）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション / ブローカー API のパスワード
   - SLACK_BOT_TOKEN : Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID : Slack チャネル ID

   オプション:
   - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL
   - DUCKDB_PATH / SQLITE_PATH : データベースファイルのパス
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト用）

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから init_schema を実行して DB とテーブルを作成します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
   ```

---

## 使い方（基本例）

以下は最小限の利用フロー例です。実運用ではログやエラーハンドリング、スケジューリングを追加してください。

1) 日次 ETL を実行（株価・財務・カレンダーの差分取得）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)  # 初回は init_schema、以後は get_connection でも可
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量構築（features テーブルを作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（signals テーブルへ書き込む）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n_signals}")
```

4) ニュース収集ジョブ（RSS から raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使用する有効な銘柄コード集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
```

5) J-Quants データ取得を直接使う（例: 日足フェッチ）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

data = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(data))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, development|paper_trading|live)
- LOG_LEVEL (任意, DEBUG|INFO|... )
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意, set=1 で .env 自動読み込みを無効化)

設定は .env（プロジェクトルート）から自動読み込みされます。自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に検出します。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル／モジュール（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py                            # 環境設定管理（.env 自動読み込み・settings）
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py                  # RSS ニュース収集・保存・銘柄抽出
    - schema.py                          # DuckDB スキーマ定義・初期化
    - stats.py                           # 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py             # 市場カレンダー管理
    - features.py                         # data の特徴量ユーティリティ（再エクスポート）
    - audit.py                            # 監査ログ DDL（signal_events, order_requests, executions 等）
    - quality.py?                         # 品質チェック（pipeline と連携、存在を想定）
  - research/
    - __init__.py
    - factor_research.py                 # Momentum/Value/Volatility 計算
    - feature_exploration.py             # 将来リターン、IC、summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py             # features テーブル構築フロー
    - signal_generator.py                # final_score 計算と signals 書き込み
  - execution/
    - __init__.py                         # 発注／実行レイヤ（実装の拡張点）
  - monitoring/                           # 監視・通知（Slack 連携等: 実装を想定）

（実際のリポジトリではさらにサブモジュールやテスト、スクリプトが存在する場合があります。）

---

## 設計上の注意点・運用時のポイント

- DuckDB の初期化は init_schema() を一度実行してください。既存テーブルはスキーマ定義で IF NOT EXISTS により保護されます。
- ETL は差分取得を基本とし、バックフィル日数（デフォルト 3 日）を用いて API 側の後出し修正を吸収します。
- J-Quants API 呼び出しにはレート制御とリトライ、401 時のトークン自動更新が入っています。大量取得時はレート制約に注意してください。
- RSS の取得では SSRF/サイズ上限/ZIP 解凍後のサイズチェック等のセーフガードがあります。
- 環境変数は .env から自動読み込みされます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能）。
- 本パッケージは「戦略のコアロジック（シグナル生成等）」と「実際のブローカー発注」を意図的に分離しています。execution 層を実装するときは冪等性・監査ログ連携を必ず行ってください。

---

## 今後の拡張ポイント（参考）

- execution 層のブローカーアダプタ実装（kabuステーション等への送信／注文管理）
- Slack 通知・モニタリングの実装（monitoring モジュール）
- 品質チェックモジュール（quality）の充実
- テストスイート（ユニット/統合テスト）と CI/CD の整備

---

必要な箇所の例や追加説明が欲しい場合は、どの操作（ETL、特徴量構築、シグナル生成、ニュース収集、スキーマ初期化など）について詳しく知りたいか教えてください。具体的なコード例や運用フローを追記します。