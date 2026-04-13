# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-13

初回公開リリース。

### 追加 (Added)
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。プロセス優先度設定・SQLite/DuckDB 接続・paper_trading モード対応・リソースクリーンアップを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用。

- 設定管理モジュールを実装 (kabusys.config)
  - プロジェクトルート自動検出による .env / .env.local の自動ロード（OS 環境変数優先、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）
  - 複雑な .env パースをサポート: `export KEY=...`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを実装
  - 必須環境変数チェック (`_require`) と各種設定プロパティ（DB パス、PID ファイル、閾値、環境判定など）
  - デフォルト値・妥当性検査（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）

- ポートフォリオ構築ライブラリを追加 (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: スコア降順選定、同点は signal_rank でタイブレーク
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）
  - risk_adjustment
    - apply_sector_cap: 既存ポジションのセクター集中上限チェック、当日売却予定銘柄の除外対応
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数
  - position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株丸め、1銘柄上限、利用可能資金に応じたスケールダウンロジック（端数の再配分アルゴリズム含む）、コストバッファ対応。

- リサーチ／ファクター計算モジュールを追加 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB ベース）
    - calc_volatility: ATR20、相対ATR、平均売買代金、出来高比率
    - calc_value: 最新財務データと株価から PER/ROE を算出
  - feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic / rank / factor_summary: ランク相関（Spearman）や統計サマリー（外部依存無しで実装）

- ニュース NLP による AI スコアリング機能を追加 (kabusys.ai.news_nlp)
  - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントスコアを取得し、ai_scores テーブルへ書き込むワークフローを実装
  - バッチ処理（最大 20 銘柄/リクエスト）、スコアクリップ（±1.0）、リトライ（429/5xx/ネットワーク）を備えた堅牢設計
  - タイムウィンドウ計算（JST ベース → UTC 変換）およびトークン肥大化対策（記事数・文字数上限）

- 運用ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト（CLI）。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定を表示。デフォルト DB は data/paper_trading.db を想定。

- ユーティリティを追加 (kabusys.utils)
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定、CPU affinity 設定ユーティリティを提供。権限がない場合は警告でスキップ。

- パッケージメタデータ
  - kabusys.__version__ = "0.1.0"

### 変更 (Changed)
- なし（初回リリースのため）

### 修正 (Fixed)
- なし（初回リリースのため）

### ドキュメント・注記 (Notes)
- 統計・ファクター計算やポートフォリオ構築は DuckDB / メモリ計算を前提とし、本番口座やブローカ API へのアクセスは行わない設計方針が示されています。
- run_execution.py は paper_trading モードで専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全に分離するよう設計されています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、配布後も動作するように実装されています。テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数があります。
- OpenAI API の使用箇所は API キーの未設定時に ValueError を投げる設計（明示的なエラー検出）。API 側の一時エラーに対しては指数バックオフでのリトライを行います。

---

今後のリリースでは、以下の改善が想定されます（例）:
- ユニットテスト追加・カバレッジ向上
- エラーハンドリング・監視のさらに詳細化（アラート送信等）
- 銘柄別単元情報の導入による position_sizing の拡張
- News NLP のレスポンス検証の強化とロギング改善

（必要であればリリースノートをより細かく分割して作成します。どのレベルの粒度を希望するか教えてください。）