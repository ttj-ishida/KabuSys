# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ基盤・研究・AI支援レジーム判定・監査ログを備えた自動売買支援ライブラリです。J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、OpenAI を使ったニュースセンチメント評価、ファクター計算・解析、監査ログスキーマなどを含むモジュール群を提供します。

---

## 主な特徴

- データ取得 / ETL
  - J-Quants API との堅牢な接続（レート制限・リトライ・トークン自動更新対応）
  - 日次差分ETL（株価・財務・市場カレンダー）
  - データ保存は DuckDB へ冪等（ON CONFLICT DO UPDATE）で行う

- ニュース収集・NLP
  - RSS フィードの安全な収集（SSRF対策・受信サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント計算（ai_scores へ保存）
  - 市場マクロセンチメントとETF MA乖離を合成して日次の市場レジーム判定（bull/neutral/bear）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ

- データ品質管理
  - 欠損検出、スパイク検出、重複チェック、日付整合性チェック（QualityIssue を返す）

- 監査・トレーサビリティ
  - シグナル → 発注要求 → 約定 の監査テーブル定義と初期化ユーティリティ
  - DuckDB ファイルまたはメモリ DB に監査用 DB を初期化する関数を提供

- 設定管理
  - .env / .env.local / 環境変数からの自動ロード（プロジェクトルート検出）
  - 必須環境変数取得時の明確なエラー提示

---

## 前提条件

- Python 3.10 以上（型注釈の pipe 演算子 `X | Y` を使用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

実行環境に応じて追加で必要になるもの（例: ネットワーク接続、J-Quants / OpenAI API キーなど）があります。

---

## インストール

開発ツリー直下で編集して使う場合（editable インストール）:

```bash
python -m pip install -U pip
python -m pip install -e .  # パッケージ化されている場合
```

必要なライブラリを個別にインストールする場合:

```bash
python -m pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt があればそれを利用してください。）

---

## 環境変数（必須項目）

主に以下の環境変数を使用します。プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に省略可：関数引数でも渡せます）

オプション:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env のパースはシェル風のクォート・コメント処理に対応します。`.env.local` は `.env` を上書きする形で読み込まれます。

---

## セットアップ手順（例）

1. リポジトリを取得 / クローン
2. 仮想環境を作る（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
3. 必要な環境変数を `.env` に設定
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
4. DuckDB スキーマや監査 DB の初期化を行う（必要に応じて）

---

## 使い方（主要な関数・ワークフロー）

以下は簡単な利用例です。実行にあたっては事前に必要な環境変数が設定されていることを確認してください。

- 日次 ETL 実行（データ取得・保存・品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアリング（OpenAI を使用）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定
print(f"written: {n_written}")
```

- 市場レジーム判定（ETF 1321 MA + マクロニュース）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（監査ログ専用DBを作成）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査用テーブルへ読み書きが可能
```

- 研究モジュール利用例（ファクター計算）:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# Zスコア正規化の使用例
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意点 / 設計上の重要事項

- Look-ahead bias（未来データ参照）回避に配慮して実装されています。
  - ETL / NLP / レジーム判定 / ファクター計算の各関数は、内部で date.today() を直に参照せず、呼び出し側が target_date を明示します。
  - DB クエリは target_date より若いデータのみを参照するよう設計されています。

- 冪等性
  - J-Quants からの保存は ON CONFLICT DO UPDATE を用いて冪等動作です。
  - news_collector は記事IDを URL 正規化 → SHA256 により生成し重複を回避します。

- エラーハンドリング
  - 各所で API エラー・ネットワークエラーに対してリトライやフォールバック（例: マクロセンチメント失敗時は 0.0）を実装しています。
  - 品質チェックは Fail-Fast せず問題を収集して呼び出し元に返します。

- テスト性
  - 外部 API 呼び出しはモジュール内の呼び出し関数（例: _call_openai_api, _urlopen）を unittest.mock で差し替え可能に設計されています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env の読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースのセンチメント評価（OpenAI）
    - regime_detector.py — ETF MA とマクロセンチメントによるレジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult 再エクスポート
    - news_collector.py  — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - stats.py           — zscore_normalize 等汎用統計ユーティリティ
    - quality.py         — 品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py           — 監査ログテーブルの DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py          — Momentum / Volatility / Value
    - feature_exploration.py      — 将来リターン / IC / summary
  - monitoring/ (※コードベースにあることを __all__ で示唆)

（上記はソース内コメント・モジュール一覧に基づく抜粋です。プロジェクト内の他ファイルも参照してください。）

---

## よくある質問 / トラブルシューティング

- .env が自動読み込まれない
  - プロジェクトルートの検出は __file__ の親ディレクトリから .git または pyproject.toml を探索します。配布後やテスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / J-Quants の接続失敗
  - ネットワークや API キーが正しいか確認してください。J-Quants クライアントは 401 を受けた場合トークンを自動リフレッシュしますが、refresh token の有効性が重要です。

- DuckDB に関する注意
  - executemany に空リストを渡すと一部の DuckDB バージョンでエラーになるため、実装側で空チェックが入っています。DB バージョンによって挙動が異なる可能性がある点にご注意ください。

---

## 貢献 / 開発

- コードはモジュール単位でテスト容易になるよう設計されています（内部API呼び出しをモック可能）。
- 新しい機能追加やバグ修正は pull request を送ってください。テストと static type check（必要なら）を推奨します。

---

README は以上です。必要であればセットアップスクリプト例や .env.example のテンプレート、より詳細な API 使用例（SQL スキーマ、テーブル定義の説明）を追加します。どの部分を拡張しましょうか？