# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、研究→戦略→発注のワークフロー（ETL / 特徴量生成 / シグナル生成 / 監査）を支援します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点の情報のみを使用）
- DuckDB を中心に冪等性（ON CONFLICT / トランザクション）を重視
- 外部依存は最小限（標準ライブラリ + 必要なライブラリ）
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）環境を想定

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション対応、トークン自動リフレッシュ、レート制御）
  - 株価日足 / 財務データ / JPX カレンダーの取得・保存
  - RSS ベースのニュース収集（前処理・URL 正規化・SSRF 対策・重複排除）
- スキーマ管理
  - DuckDB 用のスキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン
  - 日次差分 ETL（市場カレンダー → 株価 → 財務）、品質チェックへのフック
- 研究ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ
- 戦略実行支援
  - 特徴量エンジニアリング（features テーブルへの正規化保存）
  - シグナル生成（features と ai_scores を統合して BUY/SELL を生成、Bear フィルタ、エグジット判定）
- カレンダー管理
  - 営業日判定・次/前営業日計算・カレンダー差分更新ジョブ
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions などの監査テーブル定義（UUID ベースの追跡）

---

## 要件 (主な依存)

- Python 3.10+
- duckdb
- defusedxml

（必要に応じて他の標準ライブラリを使用）

インストール例（venv 想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発インストールするなら:
pip install -e .
```

※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数を設定（.env をプロジェクトルートに置く）
   - 自動 .env ロード機能が組み込まれており、プロジェクトルートにある `.env` / `.env.local` を起点に読み込みます。テストなどで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくとも開発で必要になるもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabu ステーション API パスワード（execution 層使用時）
   - SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID : Slack チャンネル ID

   オプション系（デフォルトあり）:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視 DB など（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから実行して DB を初期化します。
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   - ":memory:" を指定すればインメモリ DB が使えます。
   - 親ディレクトリが存在しない場合は自動作成されます。

---

## 使い方（主要なワークフロー例）

以下はライブラリを直接利用する際の典型的な呼び出し例です。実際は CLI やバッチジョブから呼ぶ形になることが多いです。

1) 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化済みであれば get_connection
conn = get_connection("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

2) 特徴量（features）を構築
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {count}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals generated: {total}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効な銘柄コード集合（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)
```

5) J-Quants からのデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,12,31))
```

---

## 設計上の注意・運用メモ

- 環境設定:
  - パラメータは環境変数経由で管理（Settings クラスを通してアクセス）
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます
- レート制御:
  - J-Quants クライアントは 120 req/min の制約を守るため固定間隔スロットリングを実装
- 冪等性:
  - DB 保存処理は ON CONFLICT / トランザクションで冪等化（再実行しても安全）
- ルックアヘッド対策:
  - 特徴量・シグナル生成は target_date 時点のデータのみ参照するよう設計
- テスト:
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ロギング:
  - LOG_LEVEL でログレベルを制御

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings 管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - news_collector.py            — RSS ニュース収集・保存
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       — カレンダー管理（営業日判定等）
      - features.py                  — data 側の特徴量ユーティリティ公開
      - audit.py                     — 監査ログ用スキーマ
      - ...（quality 等の補助モジュールがある想定）
    - research/
      - __init__.py
      - factor_research.py           — ファクター計算（mom/vol/value）
      - feature_exploration.py       — 将来リターン / IC / サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py       — features テーブル作成ワークフロー
      - signal_generator.py          — final_score 計算と signals 作成
    - execution/
      - __init__.py                  — 発注 / ブローカー連携層（拡張箇所）
    - monitoring/                    — 監視・メトリクス（実装場所）
- pyproject.toml / setup.cfg 等（パッケージ設定: 存在する場合）

（上記はコードベースに含まれる主要ファイルの抜粋です。実際のリポジトリでは追加の補助モジュールやテストが存在する可能性があります。）

---

## 開発・拡張ポイント

- execution 層: kabu ステーションや他ブローカー連携の実装が主目的（現在は基礎のみ）
- AI スコア統合: ai_scores テーブルを組み合わせた重み付けやレジーム判定は既実装。
- 品質チェック（quality モジュール）: ETL 後のデータ品質判定を充実させることで運用安定性を高められます。
- テスト性: jquants_client の _request / _urlopen 等はモック可能な設計（テストしやすい）

---

必要であれば、README に以下を追加できます：
- 詳細な .env.example（テンプレート）
- CI/CD / バックテストの実行方法
- SQL スキーマの ER 図・ドキュメントリンク
- 実行コマンドの systemd / cron 例

要望があれば追記します。