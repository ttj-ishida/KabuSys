# KabuSys

日本株向けの自動売買システム用ライブラリセット（データ取得・ETL・特徴量生成・シグナル生成・監視／発注用スキーマ等）。  
このリポジトリは、J-Quants API や RSS を用いたデータ収集、DuckDB を用いたデータプラットフォーム、戦略向けの特徴量加工とシグナル生成ロジックを提供します。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダー取得）
  - RSS ベースのニュース収集（SSRF／XML攻撃対策・トラッキングパラメータ除去）
- ETL / データ基盤
  - DuckDB 用スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 差分更新方式の ETL（価格・財務・カレンダー）
  - データ品質チェック（pipeline の品質チェックフローを呼べる設計）
- 研究（Research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索（将来リターン / IC / 統計サマリー）
- 戦略（Strategy）
  - 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、日付単位の冪等アップサート）
  - シグナル生成（複数コンポーネントのスコア統合、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの冪等保存）
- 実行（Execution）および監査
  - signals / signal_queue / orders / executions / positions 等の実行層スキーマ
  - 監査ログ用テーブル（signal_events / order_requests / executions 等）
- ユーティリティ
  - 環境変数 / .env ロード機能（自動ロードを制御可能）
  - 汎用統計ユーティリティ（Zスコア正規化等）

---

## 必要条件

- Python 3.10 以上（Union 型注記、型ヒントの利用により）
- DuckDB
- defusedxml（RSS パースの安全化）
- 標準ライブラリの urllib 等を使用

最低限インストールするパッケージ例:
```
pip install duckdb defusedxml
```

また、プロジェクトを編集／実行する場合は開発インストール推奨:
```
pip install -e .
```
（setup.py / pyproject.toml があることを前提にしています）

---

## セットアップ手順

1. リポジトリをクローン・配置
2. Python 環境（推奨: venv / pyenv）を作成して有効化
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   pip install -e .
   ```
4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動読み込みされます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 環境（development / paper_trading / live）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## データベース初期化（DuckDB）

初回はスキーマを作成します。簡単なスクリプト例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # 環境変数から取得（例: data/kabusys.duckdb）
conn = init_schema(db_path)
print("DB initialised:", db_path)
```

コマンドライン例:
```
python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; print(init_schema(settings.duckdb_path))"
```

init_schema は冪等で、既存のテーブルは上書きしません。

---

## 基本的な使い方（代表的な操作）

- 日次 ETL を実行（市場カレンダー取得→価格→財務→品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量のビルド（戦略用 features テーブルへ保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（features と ai_scores／positions を参照して signals を作成）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", n)
```

- ニュース収集（RSS 収集→raw_news/ news_symbols）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # など
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

---

## 開発者向け：重要ポイント・挙動

- 環境変数自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探索し、`.env` / `.env.local` を自動的に読み込みます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
- J-Quants クライアント:
  - レート制限（120 req/min）を厳守するスロットリングと、リトライ・トークン自動リフレッシュ処理を実装しています。
- 冪等性:
  - jquants_client の save_* 系、news_collector の保存処理、戦略の features / signals は冪等に設計（ON CONFLICT / トランザクションで置換）。
- DuckDB との接続:
  - 初期化は init_schema、以降の接続は get_connection を使用してください。
- セキュリティ注意:
  - RSS 収集は SSRF 対策（リダイレクト検査・プライベートIP拒否）、XML の安全パース（defusedxml）を行っています。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なディレクトリ／モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・設定取得
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py       — RSS 収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（run_daily_etl など）
    - calendar_management.py  — カレンダー更新 / 営業日ユーティリティ
    - stats.py                — 汎用統計ユーティリティ（zscore 等）
    - features.py             — features 再エクスポート
    - audit.py                — 監査ログ用スキーマ定義
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（mom/vol/value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — 正規化・ユニバースフィルタ・features 保存
    - signal_generator.py     — final_score 計算・BUY/SELL 判定・signals 保存
  - execution/                — 発注関連（空 __init__ が含まれる）
  - monitoring/               — 監視関連（将来的な拡張場所）

（詳細はソースコード内の docstring / 関数コメントを参照してください）

---

## テスト・開発ヒント

- Unit テストを書く場合は、settings の自動 .env ロードを無効化して環境を制御するか、テスト用の .env を用意してください。
- DuckDB のインメモリ DB を使うと高速なテストが可能:
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- ネットワーク呼び出し（J-Quants / RSS）はモック可能な設計になっています（関数引数でトークン注入、内部的に分割された関数など）。

---

## 注意事項 / 既知の制約

- 本モジュール群は戦略論文（StrategyModel.md 等）に基づく設計仕様を実装していますが、実運用の前に十分なバックテスト・ペーパー取引での検証が必要です。ライブ資金の投入は自己責任で行ってください。
- 一部のスキーマ制約（ON DELETE の細かな挙動など）は DuckDB のバージョン制約により保留／注釈が残されています。運用環境での運用ポリシーに応じた追加処理が必要になる場合があります。
- J-Quants API の利用に際しては API 利用規約・レート制限を確認してください。認証情報は安全に管理してください。

---

問題や改善提案があれば、実装中のモジュール（該当ファイルの docstring やログメッセージ）に沿って issue を作成してください。