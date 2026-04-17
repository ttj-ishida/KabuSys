CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。（Keep a Changelog 準拠）

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

初回公開リリース。自動売買システム「KabuSys」の基盤機能群を追加しました。
主な追加点をカテゴリ別にまとめます。

Added
- パッケージの基本情報
  - kabusys パッケージを導入。__version__ を 0.1.0 に設定。

- 環境設定 / 起動関連
  - 設定読み込みモジュール (src/kabusys/config.py)
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装。
    - .env と .env.local の読み込み順序をサポート（OS 環境変数を保護する protected 機構付き）。
    - export KEY=val 形式やクォート付き値のパース、インラインコメント処理に対応する堅牢な .env パーサを実装。
    - 設定アクセス用 Settings クラスを提供（DB パス、PID/flag パス、監視閾値、環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

  - 起動スクリプト
    - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
      - ExecutionEngine の起動フローを実装（プロセス優先度設定、DB 接続、ブローカ生成、各種依存コンポーネント組立、デーモンスレッドでの run_session 実行、停止フラグ検知による安全停止）。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATHで上書き可）。
      - 起動前に data/stop_requested.flag をチェックし、既に停止フラグがある場合は起動を中止。

    - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
      - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
      - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用（監視データは本番 DB に記録）。

  - プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分を吸収してプロセス優先度設定を行う set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を提供。
    - 実行環境で権限がない場合や未対応 OS の場合は警告ログを出してフォールバック。

- ポートフォリオ構築（純粋関数群、DB参照なし）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - シグナルのソート・候補選定 select_candidates。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分へフォールバックし WARNING ログ）。

  - リスク調整 (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限を行う apply_sector_cap（売却予定銘柄の除外、"unknown" セクターは上限適用除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバックし警告ログ）。

  - ポジションサイジング (src/kabusys/portfolio/position_sizing.py)
    - allocation_method による株数算出（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング（cost_buffer を考慮した保守的見積り）、残差処理による追加配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を実装。

  - エクスポート (src/kabusys/portfolio/__init__.py)
    - ポートフォリオ関連関数群をまとめてエクスポート。

- リサーチ / ファクター計算（DuckDB ベース）
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB SQL とウィンドウ関数で計算。
    - データ不足時の None ハンドリング、スキャン範囲のバッファ設計等、実運用を見越した実装。

  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン取得 calc_forward_returns（複数ホライズンを一括クエリで取得、horizons の検証）。
    - IC（Spearman の ρ）を計算する calc_ic（rank/同順位の平均ランク処理を含む）。
    - ファクター統計サマリ factor_summary（count/mean/std/min/max/median）。

  - research パッケージのエクスポート (src/kabusys/research/__init__.py)
    - 主要関数と zscore_normalize をまとめて公開。

- AI / ニュース NLP
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news → 銘柄別アグリゲーション → OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores テーブルへ書き戻すフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供。
    - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアクリッピングを実装。
    - OpenAI API キーが未設定の場合は ValueError を投げる明示的な挙動。
    - 出力は JSON モードを期待し、部分失敗があっても既存スコアを保護して更新する設計。

- ツール
  - Paper Trading 検証レポート生成ツール (src/kabusys/tools/paper_verification_report.py)
    - paper_trading DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、APIレイテンシ（P95）を集計してレポート出力。
    - Pass/Fail 基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - 日付フィルタ (--from/--to)、DB パス (--db) をサポート。DB が存在しない場合のエラーメッセージを出力。

Changed
- 監視関連の動作仕様
  - run_monitoring は KABUSYS_ENV に依存せず常に Settings.sqlite_path（本番想定）を使用して監視データを記録する仕様に明確化。
  - MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトへフォールバックする安全策を導入。

Fixed / Behavior improvements
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックすることでゼロ除算や不正な重み配分を回避（警告ログあり）。
- position_sizing: aggregate cap 適用時に lot_size 単位での切り下げと残差配分ロジックを実装し、available_cash を超過しないように改善。
- config: .env のパースを堅牢化（export プレフィックス、クォート内のエスケープ、コメント処理等）。

Security
- OpenAI API キーを使う機能（news_nlp）はキーが未設定の場合に明示的に例外を投げるため、無設定での誤動作を防止。

Notes / Known limitations
- process_priority: 権限不足や未対応 OS では設定がスキップされ、警告ログが出力されます（設計どおり）。
- position_sizing と apply_sector_cap は価格欠損時に一部保守的動作（スキップ）します。将来的にフォールバック価格を導入する余地あり（TODO コメントあり）。
- news_nlp は大規模 API 呼び出しを扱うため、API 利用料やレート制限に注意してください。
- DuckDB を利用したリサーチ関数は prices_daily / raw_financials 等のテーブル構造に依存します。DB スキーマの変更がある場合は SQL を更新する必要があります。

Breaking Changes
- なし（初回リリース）

Acknowledgements
- 本リリースでは外部依存として psutil、duckdb、openai を利用しています。環境に応じてインストールしてください。