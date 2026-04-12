# CHANGELOG

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
日付はソースコードから推測できる時点（2026年）を採用しています。  

## [Unreleased]

- （現時点のソースからは特定の未リリース差分は検出されていません）

---

## [0.1.0] - 2026-04-12

初期公開リリース。以下の主要機能・モジュールを実装しています。

### Added

- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数処理 (src/kabusys/config.py)
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得する仕組みを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - 空行・コメント行の無視、`export KEY=...` 形式のサポート
    - シングル/ダブル引用符付き値のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメント処理（`#` の前が空白/タブ時）
  - 各種検証とユーティリティ系プロパティを提供:
    - J-Quants / kabu API / LINE / DB パス（DuckDB/SQLite）/ PID/kill フラグ/しきい値 等
    - `PAPER_FILL_MODE` の値検証（"instant"|"partial"|"never"|"reject"）
    - `KABUSYS_ENV` (`development`/`paper_trading`/`live`) と `LOG_LEVEL` の検証

- 実行エントリポイント
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
    - プロセス優先度を High に設定して起動。
    - 環境に応じて paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockClient の想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - RiskConfig の初期値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10 等）を設定。初期ポートフォリオ値は broker.get_available_cash() を参照。

  - Monitoring 起動スクリプト (src/kabusys/run_monitoring.py)
    - プロセス優先度を High に設定して起動。
    - 監視は環境に関わらず本番 sqlite_path を使用（monitoring 用 DB 初期化を行う）。
    - DuckDB 接続も確立して SystemMonitor を初期化。
    - ポーリングループを実装。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。無効値は警告ログを出してデフォルトにフォールバック。
    - check_once() の例外を捕捉してログ出力し、ループを継続するフェイルセーフ挙動。

- 監視 DB 初期化
  - run スクリプトは init_monitoring_db を呼び出して、必要な監視テーブルが存在することを保証（冪等）。

- ユーティリティ: プロセス優先度 / CPU affinity (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装。Windows / POSIX (Linux, Darwin, FreeBSD) を吸収して psutil を用いて優先度 (nice / HIGH_PRIORITY_CLASS など) を設定。アクセス権限や未対応 OS は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) を実装。最初の N コアにプロセスをピンニング可能。入力検証あり。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder.py:
    - シグナル候補選定 select_candidates（スコア降順、同点は signal_rank 小さい方を優先）。
    - 等金額配分 calc_equal_weights、スコア重み calc_score_weights（全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: 既存保有によりセクター集中が閾値を超える場合に新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に従った発注株数算出。損切り率・risk_pct・max_position_pct・max_utilization・lot_size・cost_buffer 等のパラメータをサポート。
    - aggregate cap（全銘柄合計が available_cash を超える場合のスケーリング）、lot_size による丸め、残余キャッシュの再配分ロジックを実装。

- 研究 / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等。
    - calc_value: raw_financials から最新の財務情報を取得して PER / ROE を計算。
    - DuckDB を用いた SQL 実装、スキャン範囲や窓幅はパフォーマンス考慮で設定。
  - feature_exploration.py:
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。
    - calc_ic: スピアマンランク相関（IC）を計算。レコード不足や定数時は None を返す。
    - rank / factor_summary: 順位付け、基本統計量（count, mean, std, min, max, median）算出。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- AI ニュース NLP（OpenAI 統合） (src/kabusys/ai/news_nlp.py)
  - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）にバッチでセンチメント解析を依頼して ai_scores テーブルへ保存する処理を実装。
  - 処理フロー:
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
    - 1 銘柄あたり最大記事数・文字数でトリム（トークン膨張対策）。
    - 最大 20 銘柄ずつバッチ送信し、429/ネットワーク/5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンスの厳密 JSON バリデーション、スコアの ±1.0 クリッピング。
    - 部分失敗に備え、更新は該当コード群に対して差し替え（DELETE → INSERT）で安全に行う。
  - score_news は API キー未指定時に ValueError を送出し、呼び出し側にキー渡しを要求。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - CLI ツールを追加（python -m kabusys.tools.paper_verification_report）。
  - 指定期間の system_status / trade_logs / risk_logs を集計してレポート出力（稼働率・注文成功率・送信率・P95 レイテンシ等）。
  - 判定基準（閾値）を定義:
    - 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
  - データ不足やテーブル未存在時は安全に N/A を扱い、処理を継続。

### Changed

- （初版につき、既存コードの互換を壊す変更履歴はありません）

### Fixed / Notes

- 環境変数のパースや外部 API 呼び出し周りは堅牢性（検証・フォールバック・警告ログ）を重視して実装されているため、運用時の設定ミスに対して明確なログや例外を出します（例: MONITOR_POLL_INTERVAL の不正値は警告で 60 秒にフォールバック、PAPER_FILL_MODE の不正値は ValueError）。
- DuckDB / SQLite 接続は各 run スクリプトで適切にクローズされるよう finally ブロックで処理。
- OpenAI 呼び出しおよび外部操作はフェイルセーフ設計（API 失敗時は警告・スキップし、処理全体を停止させない）を採用。
- 一部関数内に TODO や将来的な拡張コメントあり（例: position_sizing の銘柄別 lot_size サポートや price フォールバック戦略など）。

---

注: 上記はソースコードの実装内容から推測して作成した変更履歴です。リリース日・一部文言はコードベースと注釈から推定しています。必要であれば日付やリリースの粒度（細かなパッチ/機能追加）を調整して再生成します。