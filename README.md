KabuSys — 日本株自動売買プラットフォーム (README)
=====================================

概要
----
KabuSys は日本株向けの自動売買プラットフォーム向けライブラリです。  
主に以下の責務を持つモジュール群を含みます。

- データ収集（J‑Quants API からの株価・財務・カレンダー取得、RSS ニュース収集）
- データ格納（DuckDB スキーマ定義、冪等保存）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコアの統合、BUY/SELL 判定）
- ETL パイプライン、カレンダー管理、監査ログ等のユーティリティ

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「外部 API のレート制御と堅牢性」です。

特徴一覧
--------
- J‑Quants API クライアント（トークン自動リフレッシュ、リトライ、レート制御）
- DuckDB ベースのスキーマと初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究モジュール（ファクター計算、将来リターン・IC 計算、統計サマリー）
- 特徴量作成（ユニバースフィルタ、Z スコア正規化、日付単位での UPSERT）
- シグナル生成（重み付け合成・Bear レジーム抑制・エグジット判定）
- ニュース収集（RSS 取得、前処理、記事 → 銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day）
- 監査ログ（signal → order → execution のトレーサビリティ）

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（typing の近代機能と型注釈の互換性のため）
- システムにネットワークアクセスがあること（J‑Quants / RSS 等）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されている場合）pip install -e .

   ※ 実行環境に合わせて追加パッケージをインストールしてください。  
   （例: テスト用の requests 等）

3. 環境変数／.env 設定
   このコードベースは .env ファイルまたは環境変数から設定を読み込みます。自動ロードはパッケージルート（.git または pyproject.toml がある場所）を起点に .env → .env.local の順で適用されます。
   自動ロードを無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J‑Quants 用リフレッシュトークン（必須、データ取得用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注を行う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト development）
   - LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|...、デフォルト INFO)

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

使い方（簡易ガイド）
-------------------

以下は代表的な利用例です。各操作は Python から直接呼び出して使います。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # または ":memory:"
```

2) 日次 ETL（J‑Quants からデータを差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量ビルド（feature テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点・運用上の留意事項
-----------------------
- J‑Quants API はレート制限があるため、本ライブラリは固定間隔スロットリングとリトライ戦略を実装しています。大量取得時は API 制限に注意してください。
- DuckDB のファイルは既定で data/kabusys.duckdb に保存されます。運用時はバックアップやディスク容量管理を行ってください。
- システムは "live" モードで発注処理を行う可能性があります。実際の発注を行う前に必ず設定（KABU_API_PASSWORD 等）・ログ・テストを確認してください。
- 自動環境変数ロードはプロジェクトルートを探索して .env / .env.local を読み込みます。CI 等で意図しない読み込みを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ: .env に機密情報（トークン・パスワード）を保存する場合、アクセス権限に注意してください。

ディレクトリ構成
----------------
（主要ファイル/モジュール一覧。実際のファイル構成はリポジトリに依存します。ここでは src/kabusys 以下の主要モジュールを示します。）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J‑Quants API クライアント（取得・保存）
    - news_collector.py         — RSS ニュース収集・保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - stats.py                  — 統計ユーティリティ（zscore 等）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - features.py               — データ層の小さなラッパー
    - calendar_management.py    — カレンダー管理・更新ジョブ
    - audit.py                  — 監査ログ（signal/order/execution トレース）
    - (その他: quality, …想定)
  - research/
    - __init__.py
    - factor_research.py        — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築
    - signal_generator.py       — final_score 計算と signals 生成
  - execution/                  — 発注・ブローカー接続層（骨格）
  - monitoring/                 — 監視・ログ・Slack 通知（骨格）
  - その他ユーティリティ群

開発・テスト
-------------
- 単体テスト・モックを用いたテストを行う場合、環境変数自動ロードを無効化し（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、必要な env 値をテスト側で注入してください。
- DuckDB の :memory: 接続で軽量にテスト可能です（init_schema(":memory:")）。

ライセンス / コントリビューション
--------------------------------
- 本 README の返答はコードの一部から生成したものであり、実際のライセンスはリポジトリ内の LICENSE を参照してください。  
- 機能追加・バグ修正は Pull Request にてお願いします。大きな設計変更は事前に Issue で議論してください。

補足（よくある質問）
-------------------
- Q: どの Python バージョンで動きますか？  
  A: 型ヒントや modern union 表記を使っているため Python 3.10 以上を推奨します。3.8/3.9 でも動く箇所はありますが保証対象外です。

- Q: 発注はこのライブラリ単体で行えますか？  
  A: 部分的に発注関連のスキーマや骨格は実装されていますが、実際のブローカー連携・ハンドラの実装（kabu ステーション連携のエンドポイント呼び出し等）は追加実装が必要です。運用で発注する際は十分なレビューとテストを行ってください。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であればセクションを拡張して CI 設定、運用手順、監視・アラートの例を追加できます。