# KabuSys

KabuSys は日本株向けの自動売買・研究プラットフォームです。データ取得、特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などのモジュールを備え、DuckDB を用いたデータパイプラインと分離されたバックテスト実行環境を提供します。

主な設計方針：
- ルックアヘッドバイアスの防止（取得日時の記録・ターゲット日ベースの処理）
- DuckDB を中心としたローカル分析／バックテスト
- 冪等性（DB への INSERT は ON CONFLICT/RETURNING を活用）
- ネットワーク／RSS の安全対策（SSRF 対策・XML デコード防御）
- 単純で再現性のあるポートフォリオ構築ロジック

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
    - レート制限（120 req/min）対応、リトライ・トークン自動リフレッシュ
  - RSS ニュース収集（SSRF 防御、記事正規化、銘柄コード抽出）
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
- 特徴量・シグナル（strategy）
  - features の構築（正規化・Zスコアクリップ）
  - features + AI スコアを統合したシグナル生成（BUY / SELL、レジーム判定考慮）
- ポートフォリオ構築（portfolio）
  - 候補選択、等配分・スコア加重、リスクベースのポジションサイジング
  - セクター集中制限、レジーム乗数
- バックテスト（backtest）
  - インメモリ DuckDB にデータをコピーして安全にバックテスト実行
  - 擬似約定（スリッページ・手数料モデル）、日次スナップショット、トレード記録
  - メトリクス計算（CAGR / Sharpe / MaxDD / WinRate / PayoffRatio）
  - CLI ランナー（python -m kabusys.backtest.run）
- 実行 / 監視（execution / monitoring）
  - パッケージ公開 API の一部として名前空間に含む（実装は拡張想定）

---

## 前提・依存

- Python 3.10 以上（型アノテーションに `|` を使用）
- 主要ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib を中心に HTTP を扱うため外部 HTTP クライアントは不要

（プロジェクト配布時に requirements.txt を用意してください。上記は必須の代表例です。）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone ...

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージ配布時は pip install -r requirements.txt / pip install -e . を推奨）

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須設定例（.env の例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

   注意: Settings クラスは必須キーが未設定の場合に ValueError を送出します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。

6. DuckDB スキーマ初期化
   - 本コードは `kabusys.data.schema.init_schema` の存在を前提にしています。実行前にスキーマ作成スクリプトでテーブル（prices_daily, raw_prices, raw_financials, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols など）を作成してください。
   - （スキーマ初期化関数はプロジェクト内別モジュールに実装される想定です）

---

## 使い方

以下は代表的な使用例です。

1) バックテストの実行（CLI）
- DuckDB ファイルに必要なデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）が揃っていることを前提に実行します。

例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --allocation-method risk_based \
  --max-positions 10 \
  --db path/to/kabusys.duckdb

主なオプション：
- --start / --end : YYYY-MM-DD（開始・終了日）
- --cash : 初期資金（円）
- --slippage / --commission : スリッページ・手数料率
- --allocation-method : equal | score | risk_based
- --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size 等も指定可能

2) 特徴量の構築（Python API）
- DuckDB 接続を取得後、strategy.feature_engineering.build_features を呼ぶことで target_date に対する features を計算して保存します（冪等）。

例（概念）:
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("path/to/kabusys.duckdb")
count = build_features(conn, date(2024, 1, 31))
conn.close()

3) シグナル生成（Python API）
- features / ai_scores / positions を参照して generate_signals() が signals テーブルを更新します。

例:
from kabusys.strategy import generate_signals
generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

4) ニュース収集ジョブの実行（Python API）
- RSS を取得して raw_news / news_symbols に保存します。

例（概念）:
from kabusys.data.news_collector import run_news_collection
res = run_news_collection(conn, sources=None, known_codes=set_of_codes)

5) J-Quants データ取得と保存（Python API）
- jquants_client.fetch_* → save_* を呼んでデータを取得し DuckDB に保存できます。
- トークン管理・レート制限・リトライ・ページネーションが実装されています。

---

## 主要モジュールの説明

- kabusys.config
  - Settings クラス：環境変数読み込み（.env 自動ロード、必須キー検査）
- kabusys.data
  - jquants_client.py：J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py：RSS 収集、記事正規化、銘柄抽出、DB 保存
- kabusys.research
  - factor_research.py：momentum / volatility / value 等のファクター計算
  - feature_exploration.py：将来リターン・IC・統計サマリ
- kabusys.strategy
  - feature_engineering.py：features の構築（正規化・フィルタ）
  - signal_generator.py：final_score 計算、BUY/SELL シグナル生成
- kabusys.portfolio
  - portfolio_builder.py：候補選択・重み計算
  - position_sizing.py：株数算出、リスク制御、単元丸め、aggregate cap
  - risk_adjustment.py：セクター上限・レジーム乗数
- kabusys.backtest
  - engine.py：バックテスト全体ループ（データコピー、シグナル生成呼び出し、サイジング、約定リスト管理）
  - simulator.py：擬似約定ロジック、ポートフォリオ履歴・トレード記録
  - metrics.py：バックテスト評価指標
  - run.py：CLI エントリポイント

---

## ディレクトリ構成（抜粋）

src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  └─ (schema, calendar_management 等 他モジュール想定)
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ strategy/
   │  ├─ feature_engineering.py
   │  └─ signal_generator.py
   ├─ portfolio/
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ backtest/
   │  ├─ engine.py
   │  ├─ simulator.py
   │  ├─ metrics.py
   │  └─ run.py
   ├─ execution/         # 実行層（空の __init__ など）
   └─ monitoring/        # 監視関連（将来拡張想定）

---

## 注意事項 / 運用上のポイント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を読み込みます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントは 401 を受けた際にリフレッシュトークンで ID トークンを更新し再試行します。
- NewsCollector は SSRF / XML Bomb / Gzip Bomb 対策等の防御を実装していますが、運用環境では取得先の監視・ホワイトリスト運用を推奨します。
- バックテストでは本番 DB の signals / positions を書き換えないように、対象データをインメモリ DuckDB にコピーして実行します。
- レジーム（market_regime）が不足している日付は 'bull' にフォールバックします（ログ出力あり）。
- ストップロスや売却ロジックの一部は将来的に追加実装（トレーリングストップや時間決済）を想定しています。

---

## 開発・貢献

- 新しいデータソース・出力先・実行ルールはモジュール単位で追加可能です。
- 大きな変更はユニットテスト（特に数値ロジック）と DuckDB 上での統合テストを追加してください。
- ドキュメントやスキーマ（init_schema）を合わせて更新してください。

---

以上が KabuSys の README です。README の補足（例: requirements.txt、schema の初期化スクリプト、.env.example）を用意したい場合は、テンプレートを作成して提供します。必要であればお知らせください。