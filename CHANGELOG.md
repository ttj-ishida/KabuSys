CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。日付や項目は、リポジトリ内のソースコードから推測して作成しています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基盤機能を実装。
- 設定管理:
  - Settings クラスを導入し、環境変数から各種設定を取得（KABUSYS_ENV / LOG_LEVEL / JQUANTS_REFRESH_TOKEN 等）。
  - .env と .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml）。OS 環境変数の保護（上書き禁止）に対応。
  - .env パーサーを強化: export プレフィックス・クォート文字列（バックスラッシュエスケープ）・インラインコメント処理に対応。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を実装し、不正値時に明示的なエラーを発生させる。
  - SQLite / DuckDB のデフォルトパス設定（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）を提供。

- 実行系（Execution）:
  - run_execution 起動スクリプトを追加。プロセス優先度設定、DB 接続（ペーパートレード時は専用 DB を使用）、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動（スレッド実行・停止フラグ監視）を実装。
  - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値は broker.get_available_cash() を使用して初期化。

- 監視（Monitoring）:
  - run_monitoring 起動スクリプトを追加。SystemMonitor のポーリングループを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値時はデフォルトにフォールバックして警告を出力。
  - 監視は環境に関わらず本番の sqlite_path を使用する設計。監視用 DB テーブル初期化（init_monitoring_db）を起動時に保証。

- プロセス管理ユーティリティ:
  - process_priority モジュールを追加。Windows / POSIX（Linux, Darwin, FreeBSD）を抽象化してプロセス優先度の設定（high/normal/low）を提供。
  - CPU affinity をプロセスに固定するユーティリティを実装（set_cpu_affinity）。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築（Portfolio）:
  - portfolio_builder: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合に等金額配分へフォールバックして警告。
  - risk_adjustment: セクター集中度制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知セクターは "unknown" として扱い、セクター上限の適用対象外にする設計。未知レジームは警告を出して 1.0 でフォールバック。
  - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算を実装。損切り割合・リスク許容率に基づく risk_based、各種上限（per-position / aggregate / 単元 lot_size）を考慮した丸め処理、aggregate cap 超過時のスケーリングと残差の lot 単位での再配分アルゴリズムを実装。価格未取得時のスキップやログ出力あり。

- リサーチ（Research）:
  - factor_research: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算を DuckDB 経由で実装。200日移動平均やATR、過去リターンを窓関数で算出し、データ不足時の None ハンドリングを行う。
  - feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、ファクター統計サマリ（factor_summary）、ランク化ユーティリティ（rank）を実装。外部ライブラリに依存せずに純粋関数として提供。

- AI / ニュース NLP:
  - ai/news_nlp モジュールを追加。raw_news / news_symbols から指定ウィンドウのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ格納する設計を実装。
  - 処理上の工夫: ニュースウィンドウ計算（JST→UTC 変換）、1銘柄あたりの記事数・文字数上限、最大バッチサイズ（20 銘柄）、JSON Mode 出力の想定、429/ネットワーク/5xx に対する指数バックオフ付きリトライ、レスポンスの厳格なバリデーション、スコアを ±1.0 にクリップ、部分失敗時は影響を限定するため対象コードのみ差し替える（DELETE→INSERT）方式。

- ツール:
  - tools/paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。コマンドラインで期間指定可能（--from / --to / --db）。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値に基づいて PASS/FAIL 判定を出力。データ欠損時の健全な N/A ハンドリングを行う。

Changed
- パッケージ情報:
  - パッケージの __version__ を "0.1.0" に設定。

Fixed / Robustness improvements
- .env 読み込み失敗時に警告を出すよう改善（読み込み不可ファイルは無視して継続）。
- DuckDB / SQLite 接続の確実なクローズ処理を導入（finally ブロックでクローズ）。
- run_execution / run_monitoring の停止フラグ（data/stop_requested.flag, data/kill.flag 相当のパターン）検出により安全に停止できる仕組みを導入。
- 各種関数でデータ不足・NULL 値を考慮した None ハンドリングを徹底（ファクター計算・統計・レポート生成等）。
- calc_score_weights の合計スコアが 0 の場合のフォールバック処理と警告ログ。

Security
- OpenAI API キー未設定時は明示的に ValueError を投げることで意図しない API 呼び出しを防止（ai.news_nlp）。

Notes / Known limitations
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap は price_map に price が欠損（0.0）だとエクスポージャーが過少見積もられる注釈あり。将来的にフォールバック価格の導入を検討中。
- ai/news_nlp の一部処理（記事フェッチ関数の続き）についてはソースが途中まで含まれており、実装の完全性はリポジトリ内の他ファイルに依存する可能性があります。

Authors
- KabuSys 開発チーム（ソースコードのヘッダー・モジュール構成に基づく推測）

---- 

（この CHANGELOG は、提供されたソースコードの内容から機能追加・仕様・改善点を推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）