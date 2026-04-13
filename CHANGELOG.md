CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 基本モジュール群を追加（初期リリース）。
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- 実行用エントリポイントを追加。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を "high" に設定し、環境に応じて production / paper_trading 用の SQLite DB を切り替え。DuckDB 接続を利用してエンジンを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- 設定・環境読み込み機能を実装（kabusys.config）。
  - .env/.env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - export KEY=val フォーマットやクォート・エスケープ・インラインコメントを考慮したパーサ実装。
  - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止機能。
  - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、監視閾値、PID/kill フラグパス、env/log_level 判定、paper_trading 関連設定など）。
  - 設定値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証）を導入。
- Paper Trading 検証用 CLI ツールを追加（kabusys.tools.paper_verification_report）。
  - SQLite（paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。
  - レポート期間指定オプション（--from / --to）、DB パス指定（--db）をサポート。
  - 合格基準（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ <= 200 ms）を定義して PASS/FAIL 判定を出力。
- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: select_candidates（スコア順の候補選定）、calc_equal_weights、calc_score_weights（スコア正規化、全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment: apply_sector_cap（既存保有でセクター集中が閾値を超える場合に当該セクターの新規候補を除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の配分アルゴリズム、単元株丸め、per-stock 上限、aggregate cap でスケールダウン、cost_buffer を考慮）。
  - portfolio/__init__.py で主要関数をエクスポート。
- ユーティリティ実装（kabusys.utils.process_priority）。
  - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）を吸収して優先度設定を行う。権限不足や未対応 OS はログ警告でスキップ。
  - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（None で無設定）。権限や未対応環境は警告でスキップ。
- リサーチ・ファクター計算モジュールを追加（kabusys.research）。
  - factor_research: calc_momentum（1/3/6 ヶ月リターン、MA200 乖離）、calc_volatility（ATR20、相対ATR、平均売買代金、出来高比）、calc_value（PER/ROE 計算。直近財務データ取得ロジック含む）。
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（スピアマンランク相関による IC 計算）、rank（平均ランク処理）、factor_summary（基本統計量）。
  - すべて DuckDB 接続を受け取り SQL と Python を組合せて実装、外部 API に依存しない設計。
- ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
  - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む処理を実装。
  - 処理特徴: タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）、1銘柄あたり記事数/文字数上限、バッチサイズ最大20、JSON Mode 出力の検証、429/ネットワーク/5xx に対する指数バックオフリトライ、スコアクリップ、部分更新（対象コードのみ DELETE→INSERT）により部分失敗時の保護。
  - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
- DB 初期化ユーティリティ（monitoring_db.init_monitoring_db）を run scripts から呼び出し、監視テーブルの存在を保証（冪等）。
- duckdb と sqlite の両方を接続先として利用する設計を導入（価格データやファクター計算は DuckDB、ログ/監視は SQLite）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Security
- OpenAI API キーの取り扱いは引数または環境変数を明示的に必要とし、未設定時は例外を投げることで安全性を担保。

Notes / Known limitations / 今後の改善案
- position_sizing の単元株（lot_size）は現状グローバル共通のパラメータ。将来的に銘柄別 lot_map を導入する予定（TODO コメントあり）。
- apply_sector_cap の exposure 計算は price_map に依存しており、price が 0 の場合に過少評価する可能性がある（将来的に前日終値や取得原価でフォールバックする案あり）。
- news_nlp の実装は OpenAI API のレスポンス形式に依存するため、外部仕様変更に注意。部分的に失敗しても他銘柄の既存スコアを保護する設計になっているが、完全なトランザクション処理（ロールバック等）は DuckDB 側の実装制約に依存する。
- .env パーサは一般的なケースに対応するが、極端なフォーマットの .env ファイルでは想定外の動作をする可能性がある。

参考
- 各モジュールの詳細はソース内ドキュメンテーション（docstring）を参照してください。