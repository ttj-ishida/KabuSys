# Changelog

すべての重要な変更点は Keep a Changelog の慣例に従って記載します。  
このファイルは、コードベース（src/kabusys 以下）の現状から推測して作成した初回リリース向けの変更履歴です。

全般的な注記
- バージョン: 0.1.0
- 日付: 2026-04-16（コード最終更新日を基準に推定）
- 本CHANGELOGはソースコードの内容から機能追加・振る舞いを推測してまとめたものであり、実際のコミット履歴とは一致しない可能性があります。

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 実行・監視関連の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプト。paper_trading 環境時には MockBrokerClient を利用し、Paper Trading 用の SQLite（data/paper_trading.db）に記録する機能を持つ。停止フラグ・PID 管理・デーモンスレッド実行をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計注記あり。

- 環境設定・読み込み周り
  - config.py: 
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。`.env` と `.env.local` の読み込みルール（優先順位と上書き制御）を実装。
    - export 付き、引用符あり、インラインコメントなどを考慮した堅牢な .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings クラスを導入し、アプリケーション設定（DBパス・APIキー・各種閾値・環境種別判定等）をプロパティとして提供。値検証（KABUSYS_ENV・LOG_LEVEL・PAPER_FILL_MODE 等）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を実装（レジームのフォールバック動作・ログ警告含む）。
  - portfolio/position_sizing.py: 各銘柄の発注株数を計算する calc_position_sizes を実装。risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer の考慮をサポート。

- 研究用モジュール（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value ファクターの計算を実装（prices_daily、raw_financials テーブル参照）。MA200、ATR、各種リターンの算出を SQL + DuckDB で行う。
  - research/feature_exploration.py: 将来リターン計算(calc_forward_returns)、IC（Spearman ランク相関）計算(calc_ic)、ファクター統計サマリ(factor_summary)、rank ユーティリティを提供。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP モジュール
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini）でスコアリングして ai_scores テーブルへ書き込む一連処理を実装。以下の機能を含む:
    - タイムウィンドウ計算（JSTベース→UTC換算）
    - 記事集約（1 銘柄当たり記事数・文字数上限）
    - バッチ送信（最大 20 銘柄 / 呼び出し）
    - 429 / ネットワーク / 5xx に対する指数バックオフリトライ
    - レスポンス検証とスコアの ±1.0 クリップ
    - 部分成功時に他銘柄スコアを保持するための差分置換（DELETE → INSERT）戦略
    - API キー未設定時の ValueError を明示

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を読み取り、稼働率、注文成功率、送信率、レイテンシ等の指標を算出して標準出力にレポートを出す CLI。期間フィルタ (--from / --to)、DB パス指定 (--db) をサポート。P95 計算や欠損データ時の N/A 表示、合否判定基準を実装。

- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。CPU affinity を設定する set_cpu_affinity も提供。アクセス権限不足や未対応プラットフォームを考慮した警告処理あり。

- パッケージ初期化
  - kabusys/__init__.py を追加し、__version__ = "0.1.0" を定義。主要モジュールを __all__ に公開。

### 変更 (Changed)
- DB の扱いに関する振る舞いの明示
  - 監視（run_monitoring）は KABUSYS_ENV に依存せず「本番 sqlite_path」を使用する挙動が明記されている（検証・開発時の挙動に注意が必要）。
  - 実行エンジン（run_execution）は paper_trading 環境時に専用の paper_sqlite_path を使用し、本番 DB と完全分離する設計。

- .env 読み込み順序と保護ポリシー
  - OS 環境変数 > .env.local > .env の優先順位で読み込む。既存の OS 環境変数は保護され、.env.local の override は保護キーを除いて可能。

- 環境変数・設定の検証を強化
  - Settings のプロパティ上で KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの妥当性チェックを導入。無効な設定は ValueError を発生させる。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の取り扱い改善
  - 環境変数が不正（非整数・0以下など）の場合にデフォルト値にフォールバックし、警告ログを出力するようにして time.sleep に渡す際の ValueError を回避。

- .env 読み込みでの安全性向上
  - ファイル読み込み失敗時に警告（warnings.warn）を出すようにして、読み込み障害でプロセスが落ちないように対処。

- Paper Trading レポートの堅牢化
  - DB ファイルが存在しない場合にエラーメッセージを出力して終了するように改善。テーブル欠如や SQL 実行エラー時にはデフォルトの N/A / 0 を返すフェイルセーフを実装。

- AI ニュース NLP の耐障害性
  - API 呼び出し失敗（429 / タイムアウト / 5xx 等）に対してリトライとログ出力を行い、部分失敗時にも他銘柄データを保護する書き込み戦略を実装。

### ドキュメント・注記 (Notes)
- 多くのモジュールは DuckDB 経由で prices_daily / raw_financials 等のテーブルを参照する設計になっているため、研究機能を利用するには適切な DuckDB ファイルとテーブルの準備が必要。
- portfolio/position_sizing の単元株（lot_size）は現行実装では全銘柄共通のパラメータとしているが、将来的に銘柄別の lot_size を導入する余地がある旨コメントで示されている。
- news_nlp の処理ではルックアヘッドバイアス防止のため datetime.today() / date.today() を参照しない設計方針が採られている（target_date に基づく処理）。
- process_priority や CPU affinity 設定は権限やプラットフォームに依存するため、設定失敗時は警告ログを出して処理を継続する設計。

---

今後の提案（将来的な改善候補）
- portfolio の lot_size を銘柄別に管理するための stocks マスタ導入。
- AI モジュールのテスト用モックやレート制限の詳細なメトリクス出力。
- run_monitoring/run_execution の systemd / supervisor 向けのユニットファイル・起動ドキュメント追加。
- DuckDB スキーマ定義およびサンプルデータの付属（研究機能の導入を容易にするため）。

以上。