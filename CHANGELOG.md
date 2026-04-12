# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に従っています。  

現在のリリース方針: セマンティックバージョニングに準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

初回公開リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- 実行ランナー
  - `kabusys/run_execution.py`
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は専用の SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - ブローカークライアントをファクトリ経由で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を組み込み。
    - duckdb 接続を ExecutionEngine に渡す。

- 監視ランナー
  - `kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視処理は環境に関わらず本番用の sqlite_path を使用する設計。

- 設定管理
  - `kabusys/config.py`
    - .env / .env.local の自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
    - `.env` パーサを実装（`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
    - 環境変数値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）と便利な Path プロパティ（duckdb_path, sqlite_path, paper_sqlite_path など）。
    - 起動時に OS 環境変数を保護する仕組み（読み込み時の protected セット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- ポートフォリオ構築
  - `kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（score 降順、同点時 signal_rank のタイブレーク）および最大ポジション数制約の実装。
    - 等金額配分とスコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - `kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（既存ポジションを考慮したセクター別エクスポージャ計算と候補除外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ。未知レジームはフォールバック）。
  - `kabusys/portfolio/position_sizing.py`
    - 株数決定ロジック（risk_based / equal / score）。
    - 単元（lot_size）での丸め、per-position 上限、aggregate cap（available_cash）に応じたスケールダウン処理、cost_buffer による保守的見積りを実装。
    - aggregate スケールダウン時の端数配分ロジック（fractional remainder に基づく lot 単位での追加配分）。

- リサーチ / ファクター計算
  - `kabusys/research/factor_research.py`
    - Momentum, Volatility, Value の各ファクター計算を実装（DuckDB 上で SQL による効率的実装）。
    - mom_1m/3m/6m、ma200乖離、ATR（20日）、20日平均売買代金、volume_ratio、PER/ROE などを計算。
    - データ不足時の None 扱いと行数チェック（必要サンプルが不足する場合は None）。
  - `kabusys/research/feature_exploration.py`
    - 将来リターン（forward returns）の一括取得（任意ホライズン対応、入力検証）。
    - スピアマン IC（ランク相関）計算、ランク付けユーティリティ（同順位は平均ランク）、ファクター列の統計サマリー（count/mean/std/min/max/median）。

- AI ニュース NLP スコアリング
  - `kabusys/ai/news_nlp.py`
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込むロジックを実装。
    - バッチサイズ制御（最大 20 銘柄／APIコール）、1銘柄あたり記事・文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗に備えた書き込み戦略（対象コードのみ置換）を実装。
    - ニュース集計ウィンドウの計算ユーティリティ（JST ベースのウィンドウ計算）を提供。

- ツール
  - `kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ 等の集計と基準値による Pass/Fail 判定（閾値はスクリプト内定数）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）、欠損テーブルの扱い（OperationalError を捕捉して N/A 扱い）に対応。

- プロセス制御ユーティリティ
  - `kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux, Darwin, FreeBSD）向けにプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を一元設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- パッケージ初期化
  - `kabusys/__init__.py` にバージョン情報 `__version__ = "0.1.0"` を追加。

### 変更 (Changed)
- モジュール単位の責務明確化
  - 設定・DB パス・環境判定・PID/killフラグパスなどを Settings クラスに集約し、ランナーやエンジンから直接環境変数を参照しない形に整理。
- Paper Trading 分離方針
  - 実行ランナーと各種処理が paper_trading 時に専用 SQLite を使うよう標準化（本番 DB との混在を回避）。
- DuckDB と SQLite の併用
  - 分析（DuckDB）と監視/トレードログ（SQLite）を明確に分離して利用する設計に統一。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、引用符つき値のエスケープ、インラインコメントの扱いなどに対応して自動読み込みを強化。
- ポジションサイズ計算のフォールバック動作
  - スコア加重で全銘柄のスコアが 0 の場合は等金額配分にフォールバックする旨を明示。
- 監視ループの堅牢化
  - monitor.check_once() の例外を捕捉して次のポーリングへ継続するようにし、KeyboardInterrupt を正常終了扱いに。

### その他 (Notes)
- ドキュメント参照
  - コード中に PortfolioConstruction.md / StrategyModel.md などの設計ドキュメント参照があり、アルゴリズムはそれらに基づくことを前提としています（ドキュメント本体はコードに含まれていません）。
- テスト・拡張ポイント
  - position_sizing の lot_size を銘柄別に拡張する TODO、セクターエクスポージャ計算で価格欠損時の扱い改善などの注記を残しています。
- AI モジュール
  - OpenAI API キー未設定時は ValueError を送出する設計だが、呼び出し側で運用に合わせたハンドリング（スキップ・リトライ）を推奨します。

## 廃止 (Removed)
- なし

## セキュリティ (Security)
- なし

---

参考: この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートは運用上の判断（リリース日付、パッチ番号、追加・削除の確定）に応じて調整してください。