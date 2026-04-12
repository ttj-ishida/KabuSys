KEEP A CHANGELOG の形式に準拠して、コードベースから推測した変更履歴を日本語で作成しました。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-12
--------------------
Added
- 初期公開: KabuSys パッケージの基本機能を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行/監視ランチャー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番 DB と分離。  
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - リソースは finally ブロックで確実にクローズする設計。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する点を明記。  
    - 起動時にプロセス優先度を設定し、check_once() の例外は捕捉して次ループへ継続。
- 環境設定/ローダー (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。  
  - .env と .env.local の読み込み順・上書きルールを実装（OS 環境変数保護、.env.local は上書き可能）。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。  
  - .env 行パーサーは export プレフィックス・クォート済み値・インラインコメント等に対応。  
  - 各種設定プロパティを追加・バリデーション実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。  
  - paper_trading 専用の PAPER_TRADING_SQLITE_PATH を扱うプロパティを追加。
- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。  
    - スコアゼロ時に score_weights が等金額配分にフォールバックする挙動を実装（WARNING ログ）。
  - risk_adjustment: セクター上限適用とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。  
    - 既存保有のセクター別エクスポージャ計算、売却予定コード除外などをサポート。  
    - 未知レジームでのフォールバック・警告ログ。
  - position_sizing: 発注株数計算（calc_position_sizes）。  
    - risk_based / equal / score の配分方式をサポート。  
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金によるスケーリング）、cost_buffer を考慮した保守的見積り、残額を用いた端数配分ロジックを実装。
- リサーチ（src/kabusys/research）
  - factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）。DuckDB を用いた SQL ベース実装、データ不足時の None ハンドリング。
  - feature_exploration: 将来リターン・IC・統計要約（calc_forward_returns, calc_ic, factor_summary, rank）。  
    - スピアマン（ランク相関）実装、rank は同順位を平均ランクで処理。
  - research パッケージの __all__ に主要関数をエクスポート。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングモジュールを追加。
    - タイムウィンドウ計算（calc_news_window）、記事集約、バッチ処理（最大 20 銘柄/チャンク）、JSON Mode の期待出力、429/5xx/タイムアウトに対する指数バックオフリトライ方針を明記。  
    - スコアは ±1.0 にクリップし、書き込みは部分更新（対象コードのみ差し替え）でフェイルセーフを考慮。
- ツール（src/kabusys/tools）
  - paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - CLI 引数 (--from, --to, --db) に対応。PAPER_TRADING_SQLITE_PATH を優先的に解決。  
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値（PASS/FAIL）判定とレポート出力を実装。
- ユーティリティ（src/kabusys/utils）
  - process_priority: クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。  
    - Windows / POSIX(nice) の差分吸収、権限不足や未実装 API に対する警告スキップ処理を実装。

Changed
- （初版リリースのため特になし）

Fixed
- 環境変数関連の堅牢化:
  - .env パースの強化（クォート・エスケープ・コメント処理）により誤った読み込みを軽減。
  - 自動ロード時に OS 環境変数を保護する機構を導入（.env の上書きを制御）。
- run_monitoring のポーリング間隔取得で 0 以下や不正値を検出した場合にデフォルトへフォールバックし、警告ログを出力するようにした。
- process_priority/set_cpu_affinity: 実行環境による例外（AccessDenied, NotImplementedError 等）を捕捉し、挙動を安全にスキップするようにした。

Security
- 必須のシークレット系環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）取得関数で未設定時に明確な ValueError を投げるようにし、起動時に問題が明確になるようにした。

Notes / Implementation details
- DuckDB と SQLite を併用する設計:
  - 分析用途は DuckDB（prices_daily, raw_financials 等）、運用監視やトレードログは SQLite を利用する想定。
- Paper Trading 分離:
  - paper_trading 環境では専用 SQLite を使用し、本番データと完全に分離する方針を採用。
- ログと例外処理:
  - 長時間動作を想定した監視/実行プロセスでログ出力と例外捕捉を適切に行い、フェイルセーフを重視。

（注）本 CHANGELOG は提示されたソースコードから機能と設計方針を推測して作成しています。実際のコミット履歴・差分に基づくものではありません。必要であれば項目の追加・修正を行います。