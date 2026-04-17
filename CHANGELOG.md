# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠します。

最新の変更は上に記載しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初版リリース。
- 実行系 / 監視系の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の MockBrokerClient を使用し、paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - 停止制御ファイル (data/stop_requested.flag) と PID ファイルの扱いを実装。
    - エンジンは別スレッドで実行され、停止フラグ検知時に安全に停止するループ／待機処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト: 60秒）。
    - 監視処理は環境に関わらず本番の sqlite_path を使用して監視テーブルを更新する仕様（init_monitoring_db を呼び出してテーブル存在を保証）。
    - プロセス優先度を起動時に設定（high に設定する呼び出しを実行）。

- 設定管理モジュールを追加 (kabusys.config)
  - .env ファイル自動ロード機能（プロジェクトルート検出: .git または pyproject.toml ベース）。
  - .env/.env.local の読み込み順と override 挙動（OS 環境変数を保護）。
  - export 付き行やクォート値、インラインコメント等を考慮した堅牢な .env パーサ実装。
  - Settings クラスを提供し、アプリケーション全体で利用する設定プロパティ（DB パス、API トークン、監視閾値、環境判定等）を定義。
  - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）や KABUSYS_ENV の検証（development, paper_trading, live）など入力検証を実装。

- ポートフォリオ構築関連の純粋関数群を追加 (kabusys.portfolio)
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中上限適用。unknown セクターは上限除外）、calc_regime_multiplier（レジームに応じた乗数: bull/neutral/bear）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、lot_size の扱い）。

- 研究・リサーチ機能を追加 (kabusys.research)
  - factor_research:
    - calc_momentum: モメンタム（1/3/6 か月）、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（target_date 以前の最新財務データ）。
  - feature_exploration:
    - calc_forward_returns: 翌日/翌週/翌月等の将来リターンを計算（複数ホライズン対応、入力検証あり）。
    - calc_ic, rank, factor_summary: IC（Spearman rank）計算、ランク付け、統計サマリー（count/mean/std/min/max/median）を実装。
  - 実装は pandas 等の外部依存を避け、DuckDB 接続を受けて SQL と純 Python で計算する設計。

- ニュース NLP スコアリング機能の基礎を追加 (kabusys.ai.news_nlp)
  - ニュース収集ウィンドウ計算 calc_news_window を実装（JST ベースの時間ウィンドウを UTC に変換）。
  - OpenAI API を用いたスコアリングのための score_news の骨格実装（バッチ処理・リトライ・レスポンス検証等の設計、API キー解決）。
  - 大量テキスト対策（1 銘柄当たりの最大記事数・文字数制限）やスコアの ±1.0 クリップ方針を定義。
  - （注）ファイルは一部で切れており、完全実装は今後の作業対象。

- ユーティリティを追加 (kabusys.utils)
  - process_priority:
    - set_process_priority(level): Windows / POSIX の差分を吸収して優先度(nice / HIGH_PRIORITY_CLASS 等) を設定。アクセス権限や未対応 OS の場合は安全にスキップして警告。
    - set_cpu_affinity(cpu_count): CPU affinity を最初の N コアに固定するユーティリティ（エラー時は警告してスキップ）。

- 実行・解析補助ツールを追加 (kabusys.tools.paper_verification_report)
  - Paper Trading の検証レポート生成 CLI を実装。
  - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数 等。
  - P95 計算、日付フィルタ、DB 存在チェック、しきい値による PASS/FAIL 判定（デフォルトしきい値を定義: uptime 99.0%、fill 90%、send 95%、P95 200ms）。
  - コマンドライン引数: --from, --to, --db。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。
  - DuckDB／SQLite の存在しないテーブルに対しては安全に N/A やゼロで扱うフェイルセーフを実装。

- パッケージ初期化
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。
  - 各モジュールの __all__ を整備。

### 変更 (Changed)
- 初版のため「変更」は特になし（初回公開）。

### 修正 (Fixed)
- 初版のため「修正」は特になし。

### 注意事項 / 破壊的変更 (Breaking Changes)
- 監視(run_monitoring)は環境設定に関わらず Settings.sqlite_path（本番用 sqlite）を使用する仕様になっています。paper_trading 環境で監視を動かすと本番の監視 DB にアクセスします。paper 環境で監視 DB を分離したい場合は起動方法や設定の見直しを検討してください。
- .env の自動ロードはデフォルトで有効です。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### 今後の課題 / TODO
- ai/news_nlp の score_news 処理がファイルの途中で切れており、OpenAI へのバッチ送信・レスポンス処理・DB への書き込みの完全実装が必要。
- position_sizing の price 欠損時のフォールバック価格（前日終値や取得原価など）を導入してエクスポージャーの過少見積りを改善する予定。
- 銘柄別の lot_size を取り扱える設計（現状は全銘柄共通の lot_size）への拡張。
- テストカバレッジ（ユニットテスト／統合テスト）を整備。

---

（以降のバージョンでは変更点を日付順に記録します）