# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システム向けライブラリ。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理など、研究・本番運用に必要なビルディングブロックを提供します。

## 主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）
- 特徴量構築（正規化・ユニバースフィルタ・日付単位の冪等 UPSERT）
- シグナル生成（複数コンポーネントの加重集約、Bear レジーム判定、エグジット判定）
- ニュース収集（RSS -> 前処理 -> DuckDB 保存、SSRF対策・圧縮処理）
- 監査ログ（signal -> order -> execution のトレース用テーブル定義）

## 必要条件
- Python 3.10 以上（モダンな型ヒント（|）を使用）
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

必要に応じて他のパッケージが使われることがありますが、ライブラリは標準ライブラリを多用する設計です。

例:
pip install duckdb defusedxml

あるいはプロジェクトのセットアップ時に requirements を整備してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール
   - 例:
     pip install -e .  # package を編集可能インストール（pyproject.toml がある場合）
     pip install duckdb defusedxml
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
5. DuckDB スキーマ初期化（デフォルト DB パスは data/kabusys.duckdb）
   - Python スクリプト例（後述）を実行して初期化します。

## 必須 / 推奨の環境変数
（Settings クラスで参照されます）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

.env には .env.example を参考に必要な値を設定してください。パッケージ内部の config モジュールは .git または pyproject.toml の位置を基準にプロジェクトルートを探索し .env を自動読み込みします。

## 使い方（簡単な例）

以下は最小限の使用例です。実運用ではロギング設定やエラーハンドリング、スケジューリングが必要です。

1) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は上で初期化した接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量をビルドする（strategy レイヤーの前段）
```python
from datetime import date
from kabusys.strategy import build_features
# conn は DuckDB 接続
n = build_features(conn, target_date=date(2026, 3, 20))
print(f"features upserted: {n}")
```

4) シグナルを生成する
```python
from datetime import date
from kabusys.strategy import generate_signals
# デフォルト閾値・重みで生成
count = generate_signals(conn, target_date=date(2026, 3, 20))
print(f"signals generated: {count}")
```

5) ニュース収集ジョブを走らせる
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

注意:
- 上記 API は DuckDB 接続を直接受け取ります。接続管理は呼び出し元で行ってください。
- ETL / API 呼び出しは J-Quants の認証トークンを必要とします（Settings が .env などから取得）。

## 実装上の設計ノート（抜粋）
- データ取得は差分更新 / バックフィル設計で API の後出し修正を吸収するようにしている。
- 各種保存処理は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- ニュース取得は SSRF 対策、受信サイズ制限、gzip 解凍の安全対策を実装。
- シグナル生成はルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用。
- J-Quants API はレートリミット（120 req/min）を厳守する RateLimiter を内蔵。

## 推奨運用フロー（例）
1. 夜間に calendar_update_job を実行して market_calendar を更新
2. run_daily_etl を実行して prices / financials を差分取得・保存
3. build_features を実行して features を作成
4. AI スコア・外部情報を保存（ai_scores テーブル）
5. generate_signals で売買シグナルを作成
6. execution 層で発注処理・監査ログの記録・約定反映を実行

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得＋保存用ユーティリティ）
    - news_collector.py — RSS 取得・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — zscore_normalize の再エクスポート
    - calendar_management.py — market_calendar 管理ユーティリティ（is_trading_day 等）
    - audit.py — 監査ログ用テーブル DDL
    - stats.py — z-score 正規化など統計ユーティリティ
    - (その他: quality モジュール等が存在する想定)
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化＋ユニバースフィルタ）
    - signal_generator.py — final_score 計算と signals 生成
  - execution/ — 発注・約定関連（パッケージ化用のプレースホルダ）
  - monitoring/ — 監視用ユーティリティ（プレースホルダ）

（上記はコードベースの主要モジュールを抜粋した構成です）

## ログと監視
- Settings.log_level でログレベルを制御します（環境変数 LOG_LEVEL）。
- ETLResult 等の戻り値はトラブルシュートや監査記録に便利です。run_daily_etl の戻り値から品質チェック結果やエラー一覧を取得できます。

## 開発・テストのヒント
- config モジュールはプロジェクトルート（.git / pyproject.toml）を基準に .env を自動読み込みします。ユニットテストで自動読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API 呼び出し部分は id_token の注入が可能なので、モック化しやすい設計です（jquants_client._request の挙動をモックするなど）。
- news_collector._urlopen などはテストで差し替え可能に設計されています。

## ライセンス / 貢献
リポジトリに記載の LICENSE を参照してください。バグ報告や機能改善の PR を歓迎します。

---

不明点や README に追加したい具体的な実行例・運用手順（systemd / cron / Airflow 等の統合例）があれば教えてください。必要に応じてサンプル運用スクリプトやデプロイ手順も作成します。