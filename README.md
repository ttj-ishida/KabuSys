# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。データ取得（J-Quants）、ETL、特徴量計算、戦略のシグナル生成、ニュース収集、DuckDB スキーマ管理など、研究〜運用に必要な主要コンポーネントを含んでいます。本リポジトリは発注層（証券会社とのやり取り）を部分的に想定しつつ、戦略ロジック・データ基盤・監査トレースを重視した設計になっています。

主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースの階層化スキーマ（Raw / Processed / Feature / Execution）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェックフック）
- ニュース収集（RSS）モジュール：SSRF 対策、トラッキングパラメータ除去、冪等保存
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL ルール、エグジット判定）
- 監査ログテーブル群（signal_events, order_requests, executions 等）

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 簡単な使い方（例）
- 環境変数
- ディレクトリ構成（主なファイルと役割）
- 開発メモ / 注意点

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコアライブラリです。データ基盤（DuckDB）、外部 API からのデータ取得、研究用ファクター計算、特徴量合成、シグナル生成、ニュース収集、監査ログ管理などを提供します。戦略のルックアヘッドバイアスを避ける設計方針が取られており、DB の「ある日付時点で利用可能なデータのみ」を使って計算するよう作られています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 日足・財務情報・マーケットカレンダーの取得と DuckDB への冪等保存
- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と初期化関数
- data/pipeline.py
  - 日次 ETL（差分取得、バックフィル、品質チェック呼び出し等）
- data/news_collector.py
  - RSS 収集、前処理、raw_news 保存、銘柄抽出と紐付け（SSRF 対策・サイズ制限）
- data/calendar_management.py
  - 市場カレンダー更新 / 営業日判定 / next/prev_trading_day など
- research/
  - factor_research.py: モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、統計サマリ
- strategy/
  - feature_engineering.py: ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
  - signal_generator.py: features + ai_scores を統合して BUY / SELL シグナルを生成・signals テーブルへ保存
- audit.py
  - 監査ログ（signal_events / order_requests / executions 等）の DDL 定義（初期化）

---

## 必要条件

- Python 3.10 以上（型注釈で X | None 構文を使用）
- 推奨パッケージ:
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装されている部分も多いですが、DuckDB と defusedxml は必須に近い想定です。

pip でインストールする場合の例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

（将来的には requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 3.10+ の仮想環境を作成して有効化
3. 必要ライブラリをインストール（上記参照）
4. 環境変数を設定（下記「環境変数」参照）。プロジェクトルートに `.env` / `.env.local` を配置すると自動ロードされます（ただし環境によって KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. DuckDB スキーマを初期化する

例: DuckDB を初期化する簡易コマンド
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

---

## 簡単な使い方（Python API 例）

以下は最小限のワークフロー例です。実運用ではログ設定・例外処理・スケジュール制御などが必要です。

1) DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants の refresh token を環境変数で設定しておく）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量作成（ある営業日について）
```python
from datetime import date
from kabusys.strategy import build_features
cnt = build_features(conn, date(2025, 1, 31))
print(f"features inserted: {cnt}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, date(2025, 1, 31))
print(f"signals generated: {n_signals}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードの集合（例: {'7203', '6758', ...}）
res = run_news_collection(conn, known_codes=set())
print(res)
```

---

## 環境変数

このモジュールは環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動ロードはプロジェクトルートが .git または pyproject.toml により検出された場合に行われます。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)
  - kabu ステーション API 用パスワード（execution 層で使用）
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 開発環境/ペーパートレード/本番 ("development" | "paper_trading" | "live")
- LOG_LEVEL (任意)
  - ログレベル ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL")

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイル）

以下はパッケージの主要なファイルと簡単な説明です（src/kabusys 以下）。

- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring）
- config.py
  - 環境変数のロードと Settings オブジェクト
- data/
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - schema.py — DuckDB の DDL と init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 収集と DB 保存
  - calendar_management.py — 市場カレンダー更新と営業日ユーティリティ
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — data.stats の再エクスポート
  - audit.py — 監査ログ用テーブル定義
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- strategy/
  - feature_engineering.py — ファクター正規化と features テーブルへの保存
  - signal_generator.py — final_score の算出と signals への書き込み

（execution および monitoring パッケージは初期骨格が含まれています）

---

## 開発メモ / 注意点

- Python 3.10 以上を想定しています（型注釈の新記法を使用）。
- DuckDB のバージョンや SQL の互換性に依存する箇所があります。DuckDB のメジャーアップデート時はテストを行ってください。
- J-Quants API はレート制限があるため、jquants_client は固定間隔のスロットリングとリトライ実装を備えています。テスト時は実際の API 呼び出しを避けるために id_token をモックするか、KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて設定を切ってください。
- news_collector は SSRF 対策や受信サイズ制限、XML パースの安全策（defusedxml）を導入しています。外部ソースを追加する際は検証を行ってください。
- シグナル作成は features テーブルと ai_scores テーブルのデータを前提としています。AI スコアが未登録の銘柄は中立（0.5）で補完する仕様です。
- データ更新は冪等性を重視しています（ON CONFLICT DO UPDATE / DO NOTHING を多用）。

---

必要に応じて README に実行例スクリプト、ユニットテスト / CI 設定、依存管理（pyproject.toml/requirements.txt）を追加することを推奨します。README の追記や操作手順の補足が必要であれば教えてください。