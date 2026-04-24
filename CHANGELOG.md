CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
リリース日はコードベースの現在日付（2026-04-24）を使用しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 実行用エントリスクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。プロセス優先度設定、停止フラグ監視、paper_trading 用の専用 SQLite を使用する分離動作等を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグで安全に終了。
- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI（入力補助、シークレットマスク、既存値の読み込み・再利用をサポート）。
  - validate_config.py: .env と config/*.yaml の起動前検証ツール。必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML 任意）、本番環境向けガードを含む。--strict で警告を FAIL として扱う。
- 設定管理
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数保護）と細かなパースロジックを実装。Settings クラスを導入し、J-Quants / kabu API / DB パス / paper_trading 切替 /監視閾値 /ログレベル等のプロパティを提供。無効値検出で明確な例外を返す。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテートのファイルハンドラを統一的に設定する setup_logging を追加（ログディレクトリ自動作成、既存ハンドラのクリア、ログレベル解決ロジック）。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加（psutil ベース、許可エラーは警告でスキップ）。
- ポートフォリオ構築関連モジュール
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク）と等金額／スコア重み付け関数を実装。スコアが全て 0 の場合は等分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（既存保有からのセクター比率計算と候補除外）および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear 対応、未知レジームは警告とフォールバック）。
  - portfolio/position_sizing.py: 各配分方式（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、残余配分ロジック、コストバッファ考慮などを含む。
  - portfolio/__init__.py: 主要関数をエクスポートするパッケージ初期化。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading 用 SQLite を解析して検証レポートを生成する CLI。システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）やリスク却下数を集計し PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB 存在チェック、出力フォーマットを実装。
- パッケージ基礎
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- DB 周りの取り扱い方針を明確化
  - 監視 (monitoring) は環境にかかわらず本番 sqlite_path を使用する（run_monitoring）。
  - 実行エンジンは paper_trading の場合に paper_sqlite_path を使用して本番 DB と完全分離する（run_execution）。
- ログ動作の一貫化
  - 全起動スクリプトで setup_logging を呼び出すことを想定し、ログの出力先・回転設定を統一。

Fixed
- .env パーサの改善
  - export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理、コメント判定ルール等を実装し、より実用的な .env 解析を実現。
- UUID / PID / stop フラグ周りの扱いを標準化
  - data ディレクトリ下の停止フラグ・PID ファイルパスを定義し、起動・停止時の安全な挙動を確保（run_execution/run_monitoring）。

Security
- 環境変数取り扱いの安全性向上
  - config_setup の出力に注意書き（.env を Git にコミットしない）を追加。Settings は必須変数未設定時に明示的に例外を投げる。

Documentation / CLI
- 各 CLI スクリプトにヘルプと使用例を追加（ファイルトップの docstring や argparse による説明）。
- validate_config と config_setup に使用手順・注意事項の出力を追加。

Internal / Misc
- duckdb を分析用 DB として採用する点を明記（run_* スクリプトが duckdb 接続を渡す設計）。
- utils/logging_setup はログディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
- process_priority:set_cpu_affinity を追加し、利用可能コア数チェック・安全弁を導入。

Notes / Known issues
- research/factor_research.py はモジュールの骨組み（定数・関数署名）とモメンタム計算の導入部が含まれますが、ソースの表示が途中で切れており（ファイル末尾で断片的な行が存在）、完全実装・テストは必要です。
- 一部の TODO コメントにある将来的拡張（銘柄別 lot_size の導入、価格フォールバックなど）は未実装。

今後の予定
- research/factor_research の完全実装と単体テスト追加
- E2E テスト（paper_trading と live の振る舞い差分検証）
- strategies / execution の統合テストおよび運用監視ルール強化

---

参考:
- 主要ファイル: src/kabusys/{config.py,config_setup.py,validate_config.py,run_execution.py,run_monitoring.py,utils/logging_setup.py,utils/process_priority.py,portfolio/,tools/paper_verification_report.py,__init__.py}
- 各 CLI は python -m kabusys.<module> で実行可能（各ファイル冒頭の docstring を参照）。