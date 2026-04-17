# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py に定義された __version__ に準拠しています。

現在のリリース
---------------

Unreleased
---------
- 開発中の変更はここに記載します。

[0.1.0] - 2026-04-17
-------------------
Added
- プロジェクト初回リリース（ベース機能を追加）
  - 基本情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 設定管理
    - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（src/kabusys/config.py）。
    - .env パース機能を強化：export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、行内コメントの扱いを考慮（src/kabusys/config.py）。
    - Settings クラスに各種設定プロパティを実装（DB パス、KABUSYS_ENV 判定、paper_trading 用パス、監視閾値など）（src/kabusys/config.py）。
  - 設定ユーティリティ / CLI
    - 対話式環境設定ウィザードを実装（.env の初期作成・更新、シークレットマスク表示、確認プロンプト）（src/kabusys/config_setup.py）。
    - 起動前設定検証 CLI を実装（必須環境変数・パス・YAML ファイルの存在・本番ガード等をチェック、--strict オプションで警告を FAIL 扱いに可能）（src/kabusys/validate_config.py）。
  - 実行 / 監視エントリポイント
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用 DB に分離して記録（src/kabusys/run_execution.py）。
      - 停止フラグ（data/stop_requested.flag）検出時の安全停止、PID ファイル管理、スレッドでのエンジン実行制御を実装。
    - SystemMonitor ポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検出、例外時のログ継続）（src/kabusys/run_monitoring.py）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - データベース / 分析
    - DuckDB / SQLite の接続サポートを組み込み（各種モジュールで使用。duckdb/ sqlite3 経由でのデータ読み書き実装）。
    - 監視 DB 初期化ユーティリティを呼び出す仕組みを導入（init_monitoring_db を各起動時に冪等に実行）。
  - Portfolio（銘柄選定・配分・サイズ決定）
    - 候補選定・重み計算（等配分・スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
      - スコア合計が 0 の場合は等金額配分にフォールバックして警告を出力。
    - セクター集中制限、レジーム乗数ロジックを実装（apply_sector_cap、calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
      - unknown セクターの取り扱いや、レジーム不明時のフォールバックを明示。
    - 株数計算（risk_based / equal / score）・単元株丸め・aggregate スケールダウンロジックを実装（src/kabusys/portfolio/position_sizing.py）。
      - lot_size 単位で丸め、コストバッファ（手数料・スリッページ）を考慮した計算、available_cash 超過時のスケールダウン・残差配分アルゴリズムを搭載。
  - リサーチ（ファクター計算）
    - Momentum / Volatility 等のファクター計算モジュールを実装（duckdb を用いた SQL ベースの集計。prices_daily / raw_financials に依存）（src/kabusys/research/factor_research.py）。
      - 1M/3M/6M リターン、MA200 乖離、20日 ATR、20日平均出来高、volume ratio 等を計算。
  - ツール
    - Paper Trading の検証レポート生成スクリプトを追加（P95 計算、稼働率・注文成功率・送信率・レイテンシ判定・閾値による PASS/FAIL 出力）（src/kabusys/tools/paper_verification_report.py）。
      - DB 存在チェック、期間フィルタ（--from/--to）サポート、欠損テーブル時の耐障害処理。
  - ユーティリティ
    - プロセス優先度 / CPU affinity 設定ユーティリティを追加（Windows / POSIX の違いを吸収し例外時は警告でスキップ）（src/kabusys/utils/process_priority.py）。
      - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
  - パッケージ初期化
    - パッケージエクスポートを整理（portfolio モジュールの公開関数等）（src/kabusys/portfolio/__init__.py）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- config_setup が生成する .env ヘッダに「.env を絶対に Git にコミットしないこと」を明記（src/kabusys/config_setup.py）。

Notes / Implementation details
- .env の自動ロードは実行環境の OS 環境変数を保護する設計（.env の上書きを保護する protected セットを利用）。
- Paper Trading と Live のデータ分離を明確に設計（paper_sqlite_path の使用）。
- 監視と実行は外部停止フラグファイル（data/stop_requested.flag）でプロセス間連携/強制停止を実現。

今後の予定（例）
- stocks マスタによる銘柄別 lot_size の導入（position_sizing の拡張）
- ファクター計算の追加、正規化ユーティリティの公開拡充
- テストカバレッジ拡充・CI パイプライン整備

-------------------
参考: 主なファイル一覧
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/portfolio/*
- src/kabusys/research/factor_research.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

以上。